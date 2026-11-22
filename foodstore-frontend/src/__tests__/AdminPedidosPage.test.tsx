/**
 * Pruebas unitarias y de integración para `AdminPedidosPage`, `useAdminPedidos` y `cambiarEstadoPedido` (`E9.3`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Reglas `RN-02`, `RN-03`, `RN-04`, `RN-05`, historia `HU-TPI-05` y ruta `/admin/pedidos` (págs. 5, 14, 18–20).
 */
import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  AxiosError,
  type AxiosAdapter,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'
import type { ReactNode } from 'react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { UserPublic } from '@/features/auth'
import { AdminPedidosPage, type EstadoPedido, type PedidoRead } from '@/features/pedidos'
import { formatPrecio } from '@/features/productos'
import { AppRoutes } from '@/routes/AppRouter'
import { axiosInstance } from '@/shared/api/axiosInstance'
import { queryClient } from '@/shared/api/queryClient'
import { registerAuthInterceptorHandlers, useAuthStore } from '@/store/authStore'

const originalAdapter = axiosInstance.defaults.adapter

const USER_ADMIN: UserPublic = {
  id: 1,
  username: 'admin',
  full_name: 'Administrador',
  email: 'admin@example.com',
  role: 'admin',
  disabled: false,
  created_at: '2026-11-20T12:00:00Z',
}

const USER_CLIENTE: UserPublic = {
  id: 2,
  username: 'cliente1',
  full_name: 'Cliente Uno',
  email: 'cliente1@example.com',
  role: 'user',
  disabled: false,
  created_at: '2026-11-20T12:00:00Z',
}

function makePedido(
  id: number,
  estado: EstadoPedido,
  overrides: Partial<PedidoRead> = {},
): PedidoRead {
  return {
    id,
    usuario_id: 10 + id,
    estado,
    forma_pago: id % 2 === 0 ? 'TRANSFERENCIA' : 'EFECTIVO',
    direccion_entrega: `Calle Falsa ${100 + id}`,
    notas: id === 1 ? 'Timbre B' : null,
    total: 1000 * id,
    created_at: `2026-11-20T1${Math.min(id, 9)}:00:00Z`,
    updated_at: `2026-11-20T1${Math.min(id, 9)}:05:00Z`,
    items: [
      {
        producto_id: 100 + id,
        nombre_producto: `Producto ${id}`,
        precio_unitario: 500 * id,
        cantidad: 2,
        subtotal: 1000 * id,
      },
    ],
    ...overrides,
  }
}

const SAMPLE_PEDIDOS: PedidoRead[] = [
  makePedido(1, 'PENDIENTE'),
  makePedido(2, 'EN_PREPARACION'),
  makePedido(3, 'ENTREGADO'),
  makePedido(4, 'CANCELADO'),
]

function createAxiosResponse(
  config: InternalAxiosRequestConfig,
  status: number,
  data: unknown,
): AxiosResponse {
  return {
    data,
    status,
    statusText: String(status),
    headers: {},
    config,
  }
}

function createAxiosHttpError(
  config: InternalAxiosRequestConfig,
  status: number,
  data: unknown,
): AxiosError {
  const response = createAxiosResponse(config, status, data)
  return new AxiosError(
    `Request failed with status code ${status}`,
    AxiosError.ERR_BAD_REQUEST,
    config,
    undefined,
    response,
  )
}

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="current-path">{location.pathname}</div>
}

function renderWithProviders(ui: ReactNode, initialEntries: string[] = ['/admin/pedidos']) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  localStorage.clear()
  queryClient.clear()
  queryClient.setDefaultOptions({ queries: { retry: false } })
  registerAuthInterceptorHandlers()
  useAuthStore.setState({ usuario: null, cargando: false, error: null })
})

afterEach(() => {
  axiosInstance.defaults.adapter = originalAdapter
  queryClient.clear()
  queryClient.setDefaultOptions({ queries: { retry: 1 } })
  localStorage.clear()
  vi.restoreAllMocks()
})

describe('AdminPedidosPage (E9.3)', () => {
  it('redirige a /login sin sesión y a /unauthorized para rol user en /admin/pedidos', async () => {
    const firstRender = renderWithProviders(
      <>
        <AppRoutes />
        <LocationProbe />
      </>,
    )

    expect(await screen.findByTestId('current-path')).toHaveTextContent('/login')
    firstRender.unmount()

    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })
    renderWithProviders(
      <>
        <AppRoutes />
        <LocationProbe />
      </>,
    )

    expect(await screen.findByTestId('current-path')).toHaveTextContent('/unauthorized')
  })

  it('muestra Skeleton inicial, lista pedidos en tabla semántica y respeta botones RN-02 por estado', async () => {
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })

    let resolveFetch!: (res: AxiosResponse) => void
    const adapter: AxiosAdapter = (config) => {
      if (config.url === '/pedidos' && config.method?.toLowerCase() === 'get') {
        expect(config.params).toEqual({ limit: 100, skip: 0 })
        return new Promise<AxiosResponse>((resolve) => {
          resolveFetch = resolve
        })
      }
      return Promise.reject(createAxiosHttpError(config, 404, { detail: 'No encontrado' }))
    }
    axiosInstance.defaults.adapter = adapter

    renderWithProviders(<AdminPedidosPage />)

    expect(screen.getByRole('status')).toHaveTextContent('Cargando pedidos…')

    await waitFor(() => expect(resolveFetch).toBeTypeOf('function'))
    resolveFetch(
      createAxiosResponse({} as InternalAxiosRequestConfig, 200, {
        total: SAMPLE_PEDIDOS.length,
        items: SAMPLE_PEDIDOS,
      }),
    )

    const table = await screen.findByRole('table')
    const rows = within(table).getAllByRole('row')
    // 1 header + 4 data rows
    expect(rows).toHaveLength(5)

    // Row 1: PENDIENTE -> Avanzar a En preparación + Cancelar + Ver detalle
    expect(within(rows[1]).getByText('#1')).toBeInTheDocument()
    expect(within(rows[1]).getByText('Pendiente')).toBeInTheDocument()
    expect(within(rows[1]).getByText(formatPrecio(1000).replace(/\u00a0/g, ' '))).toBeInTheDocument()
    expect(
      within(rows[1]).getByRole('button', { name: 'Avanzar a En preparación' }),
    ).toBeInTheDocument()
    expect(within(rows[1]).getByRole('button', { name: 'Cancelar' })).toBeInTheDocument()
    expect(within(rows[1]).getByRole('button', { name: 'Ver detalle' })).toBeInTheDocument()

    // Row 2: EN_PREPARACION -> Marcar Entregado + Cancelar + Ver detalle
    expect(within(rows[2]).getByText('#2')).toBeInTheDocument()
    expect(within(rows[2]).getByText('En preparación')).toBeInTheDocument()
    expect(within(rows[2]).getByRole('button', { name: 'Marcar Entregado' })).toBeInTheDocument()
    expect(within(rows[2]).getByRole('button', { name: 'Cancelar' })).toBeInTheDocument()

    // Row 3: ENTREGADO -> sin botones de transición
    expect(within(rows[3]).getByText('#3')).toBeInTheDocument()
    expect(within(rows[3]).getByText('Entregado')).toBeInTheDocument()
    expect(
      within(rows[3]).queryByRole('button', { name: 'Avanzar a En preparación' }),
    ).not.toBeInTheDocument()
    expect(
      within(rows[3]).queryByRole('button', { name: 'Marcar Entregado' }),
    ).not.toBeInTheDocument()
    expect(within(rows[3]).queryByRole('button', { name: 'Cancelar' })).not.toBeInTheDocument()
    expect(within(rows[3]).getByRole('button', { name: 'Ver detalle' })).toBeInTheDocument()

    // Row 4: CANCELADO -> sin botones de transición
    expect(within(rows[4]).getByText('#4')).toBeInTheDocument()
    expect(within(rows[4]).getByText('Cancelado')).toBeInTheDocument()
    expect(within(rows[4]).queryByRole('button', { name: 'Cancelar' })).not.toBeInTheDocument()
  })

  it('filtra por estado y búsqueda textual, reinicia a pageIndex 0 y muestra EstadoVacio con Limpiar filtros', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })

    // 12 pedidos para probar paginación (página 1 de 10, página 2 de 2) y reset a pageIndex 0
    const manyPedidos: PedidoRead[] = Array.from({ length: 12 }, (_, idx) => {
      const id = idx + 1
      const estado: EstadoPedido = id <= 6 ? 'PENDIENTE' : 'ENTREGADO'
      return makePedido(id, estado)
    })

    axiosInstance.defaults.adapter = async (config) => {
      if (config.url === '/pedidos' && config.method?.toLowerCase() === 'get') {
        return createAxiosResponse(config, 200, {
          total: manyPedidos.length,
          items: manyPedidos,
        })
      }
      throw createAxiosHttpError(config, 404, { detail: 'No encontrado' })
    }

    renderWithProviders(<AdminPedidosPage />)

    await screen.findByRole('table')
    expect(screen.getByText('Página 1 de 2 (12 pedidos)')).toBeInTheDocument()

    // Avanzar a página 2
    await user.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(screen.getByText('Página 2 de 2 (12 pedidos)')).toBeInTheDocument()
    expect(screen.getByText('#11')).toBeInTheDocument()

    // Filtrar por estado PENDIENTE -> debe resetear a página 1
    await user.selectOptions(screen.getByLabelText('Filtrar por estado'), 'PENDIENTE')
    expect(screen.getByText('Página 1 de 1 (6 pedidos)')).toBeInTheDocument()
    expect(screen.getByText('#1')).toBeInTheDocument()
    expect(screen.queryByText('#7')).not.toBeInTheDocument()

    // Búsqueda textual sin coincidencias -> EstadoVacio con Limpiar filtros
    await user.type(screen.getByLabelText('Buscar pedido'), 'inexistente-xyz')
    expect(screen.getByText('No se encontraron pedidos con esos filtros')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Limpiar filtros' }))
    expect(screen.getByText('Página 1 de 2 (12 pedidos)')).toBeInTheDocument()
  })

  it('ordena columnas con <th scope="col" aria-sort> y <button type="button">', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })

    axiosInstance.defaults.adapter = async (config) => {
      if (config.url === '/pedidos' && config.method?.toLowerCase() === 'get') {
        return createAxiosResponse(config, 200, {
          total: SAMPLE_PEDIDOS.length,
          items: SAMPLE_PEDIDOS,
        })
      }
      throw createAxiosHttpError(config, 404, { detail: 'No encontrado' })
    }

    renderWithProviders(<AdminPedidosPage />)

    const table = await screen.findByRole('table')
    const totalHeader = within(table).getByRole('columnheader', { name: /Total/i })
    expect(totalHeader).toHaveAttribute('scope', 'col')
    expect(totalHeader).toHaveAttribute('aria-sort', 'none')

    const sortBtn = within(totalHeader).getByRole('button')
    await user.click(sortBtn)
    expect(totalHeader).toHaveAttribute('aria-sort', 'descending')

    const rowsDesc = within(table).getAllByRole('row')
    // En orden descendente por total, #4 (4000) es primero
    expect(within(rowsDesc[1]).getByText('#4')).toBeInTheDocument()

    await user.click(sortBtn)
    expect(totalHeader).toHaveAttribute('aria-sort', 'ascending')

    const rowsAsc = within(table).getAllByRole('row')
    expect(within(rowsAsc[1]).getByText('#1')).toBeInTheDocument()
  })

  it('ejecuta transición válida según RN-02 e invalida pedidos, detalle, resumen y productos', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })

    let pedidosState = SAMPLE_PEDIDOS.map((p) => ({ ...p }))
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    axiosInstance.defaults.adapter = async (config) => {
      const method = config.method?.toLowerCase()
      if (config.url === '/pedidos' && method === 'get') {
        return createAxiosResponse(config, 200, {
          total: pedidosState.length,
          items: pedidosState,
        })
      }
      if (config.url === '/pedidos/1/estado' && method === 'patch') {
        const body = typeof config.data === 'string' ? JSON.parse(config.data) : config.data
        expect(body).toEqual({ estado: 'EN_PREPARACION' })
        const updated: PedidoRead = { ...pedidosState[0], estado: 'EN_PREPARACION' }
        pedidosState = pedidosState.map((p) => (p.id === 1 ? updated : p))
        return createAxiosResponse(config, 200, updated)
      }
      throw createAxiosHttpError(config, 404, { detail: 'No encontrado' })
    }

    renderWithProviders(<AdminPedidosPage />)

    const table = await screen.findByRole('table')
    const row1 = within(table).getAllByRole('row')[1]
    await user.click(within(row1).getByRole('button', { name: 'Avanzar a En preparación' }))

    await waitFor(() => {
      const refreshedRow1 = within(screen.getByRole('table')).getAllByRole('row')[1]
      expect(within(refreshedRow1).getByText('En preparación')).toBeInTheDocument()
      expect(
        within(refreshedRow1).getByRole('button', { name: 'Marcar Entregado' }),
      ).toBeInTheDocument()
    })

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['pedidos'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['pedidos', 1] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['pedidos', 'resumen'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['productos'] })
  })

  it('ante error 400 en transición muestra role="alert" y conserva el pedido y su estado confirmado', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })

    axiosInstance.defaults.adapter = async (config) => {
      const method = config.method?.toLowerCase()
      if (config.url === '/pedidos' && method === 'get') {
        return createAxiosResponse(config, 200, {
          total: SAMPLE_PEDIDOS.length,
          items: SAMPLE_PEDIDOS,
        })
      }
      if (config.url === '/pedidos/1/estado' && method === 'patch') {
        throw createAxiosHttpError(config, 400, {
          detail: 'Transición de estado inválida según RN-02',
        })
      }
      throw createAxiosHttpError(config, 404, { detail: 'No encontrado' })
    }

    renderWithProviders(<AdminPedidosPage />)

    const table = await screen.findByRole('table')
    const row1 = within(table).getAllByRole('row')[1]
    await user.click(within(row1).getByRole('button', { name: 'Avanzar a En preparación' }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Transición de estado inválida según RN-02')

    // El pedido #1 conserva su estado confirmado 'Pendiente'
    const currentRow1 = within(screen.getByRole('table')).getAllByRole('row')[1]
    expect(within(currentRow1).getByText('Pendiente')).toBeInTheDocument()
  })

  it('abre el modal de detalle snapshot RN-05 con datos del pedido e ítems formateados', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })

    axiosInstance.defaults.adapter = async (config) => {
      if (config.url === '/pedidos' && config.method?.toLowerCase() === 'get') {
        return createAxiosResponse(config, 200, {
          total: SAMPLE_PEDIDOS.length,
          items: SAMPLE_PEDIDOS,
        })
      }
      throw createAxiosHttpError(config, 404, { detail: 'No encontrado' })
    }

    renderWithProviders(<AdminPedidosPage />)

    const table = await screen.findByRole('table')
    const row1 = within(table).getAllByRole('row')[1]
    await user.click(within(row1).getByRole('button', { name: 'Ver detalle' }))

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('Detalle del pedido #1')).toBeInTheDocument()
    expect(within(dialog).getByText('Calle Falsa 101')).toBeInTheDocument()
    expect(within(dialog).getByText('Timbre B')).toBeInTheDocument()
    expect(within(dialog).getByText('Producto 1')).toBeInTheDocument()
    const normalize = (value: string) => value.replace(/\u00a0/g, ' ')
    expect(within(dialog).getByText(normalize(formatPrecio(500)))).toBeInTheDocument()
    expect(within(dialog).getAllByText(normalize(formatPrecio(1000))).length).toBeGreaterThanOrEqual(2)

    await user.click(within(dialog).getByRole('button', { name: 'Cerrar' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('conserva datos previos y muestra aviso inline-refetch si falla una actualización posterior', async () => {
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })

    let callCount = 0
    axiosInstance.defaults.adapter = async (config) => {
      if (config.url === '/pedidos' && config.method?.toLowerCase() === 'get') {
        callCount += 1
        if (callCount === 1) {
          return createAxiosResponse(config, 200, {
            total: SAMPLE_PEDIDOS.length,
            items: SAMPLE_PEDIDOS,
          })
        }
        throw createAxiosHttpError(config, 500, { detail: 'Error temporal del servidor' })
      }
      throw createAxiosHttpError(config, 404, { detail: 'No encontrado' })
    }

    renderWithProviders(<AdminPedidosPage />)
    await screen.findByRole('table')

    await queryClient.invalidateQueries({ queryKey: ['pedidos', 'admin'] })

    const status = await screen.findByRole('status')
    expect(status).toHaveTextContent(/No se pudieron actualizar los pedidos/i)
    expect(screen.getByText('#1')).toBeInTheDocument()
  })
})
