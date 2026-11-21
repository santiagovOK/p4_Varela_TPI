/**
 * Pruebas unitarias y de integración para `MisPedidosPage`, `PedidoDetallePage` y `useCancelarPedido` (`E8.4`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Reglas `RN-03`, `RN-04`, `RN-05` y `HU-TPI-03` (págs. 5, 13–14, 18–20).
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
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { UserPublic } from '@/features/auth'
import {
  MisPedidosPage,
  PEDIDOS_QUERY_KEY,
  PEDIDOS_RESUMEN_QUERY_KEY,
  PRODUCTOS_ROOT_QUERY_KEY,
  PedidoDetallePage,
  type PedidoRead,
  type PedidosPaginados,
} from '@/features/pedidos'
import { AppRoutes } from '@/routes/AppRouter'
import { axiosInstance } from '@/shared/api/axiosInstance'
import { queryClient } from '@/shared/api/queryClient'
import { registerAuthInterceptorHandlers, useAuthStore } from '@/store/authStore'

const originalAdapter = axiosInstance.defaults.adapter

const USER_CLIENTE: UserPublic = {
  id: 2,
  username: 'cliente1',
  full_name: 'Cliente Uno',
  email: 'cliente1@example.com',
  role: 'user',
  disabled: false,
  created_at: '2026-11-20T12:00:00Z',
}

function makePedido(overrides: Partial<PedidoRead> = {}): PedidoRead {
  return {
    id: 10,
    usuario_id: 2,
    estado: 'PENDIENTE',
    forma_pago: 'EFECTIVO',
    direccion_entrega: 'Av. Colón 1234',
    notas: null,
    total: 14800,
    created_at: '2026-11-20T15:30:00Z',
    updated_at: '2026-11-20T15:30:00Z',
    items: [
      {
        producto_id: 1,
        nombre_producto: 'Hamburguesa Clásica',
        precio_unitario: 6500,
        cantidad: 2,
        subtotal: 13000,
      },
      {
        producto_id: 3,
        nombre_producto: 'Gaseosa Cola 500ml',
        precio_unitario: 1800,
        cantidad: 1,
        subtotal: 1800,
      },
    ],
    ...overrides,
  }
}

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

function renderWithProviders(
  ui: ReactNode,
  initialEntries: Array<string | { pathname: string; state?: unknown }> = ['/mis-pedidos'],
) {
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

describe('MisPedidosPage y PedidoDetallePage (E8.4)', () => {
  it('redirige a /login cuando no hay sesión activa en /mis-pedidos y /mis-pedidos/:id', async () => {
    renderWithProviders(
      <>
        <AppRoutes />
        <LocationProbe />
      </>,
      ['/mis-pedidos'],
    )

    await waitFor(() => {
      expect(screen.getByTestId('current-path')).toHaveTextContent('/login')
    })

    renderWithProviders(
      <>
        <AppRoutes />
        <LocationProbe />
      </>,
      ['/mis-pedidos/10'],
    )

    await waitFor(() => {
      expect(screen.getAllByTestId('current-path').at(-1)).toHaveTextContent('/login')
    })
  })

  it('muestra Skeleton en carga inicial, EstadoVacio sin pedidos y EstadoError inline-refetch no destructivo si falla una recarga', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })

    let resolveInitial!: (response: AxiosResponse) => void
    let callCount = 0

    const adapter: AxiosAdapter = vi.fn((config) => {
      callCount += 1
      if (callCount === 1) {
        return new Promise<AxiosResponse>((resolve) => {
          resolveInitial = resolve
        })
      }
      if (callCount === 2) {
        return Promise.resolve(
          createAxiosResponse(config, 200, {
            total: 1,
            items: [makePedido({ id: 21, estado: 'ENTREGADO' })],
          } satisfies PedidosPaginados),
        )
      }
      return Promise.reject(
        createAxiosHttpError(config, 500, { detail: 'Error temporal del servidor' }),
      )
    })

    axiosInstance.defaults.adapter = adapter

    const { rerender } = renderWithProviders(<MisPedidosPage />)

    // Carga inicial muestra Skeleton accesible
    expect(screen.getByRole('status')).toHaveAttribute('aria-busy', 'true')

    await waitFor(() => {
      expect(resolveInitial).toBeTypeOf('function')
    })

    // Resuelve con lista vacía
    resolveInitial(
      createAxiosResponse({} as InternalAxiosRequestConfig, 200, {
        total: 0,
        items: [],
      } satisfies PedidosPaginados),
    )

    expect(
      await screen.findByText('Todavía no realizaste pedidos'),
    ).toBeInTheDocument()

    // Cambiamos filtro a ENTREGADO -> carga pedido confirmado (#21)
    await user.selectOptions(screen.getByLabelText('Filtrar por estado'), 'ENTREGADO')
    expect(await screen.findByText('Pedido #21')).toBeInTheDocument()

    // Cambiamos filtro a PENDIENTE -> falla refetch, pero conserva Pedido #21 visible
    await user.selectOptions(screen.getByLabelText('Filtrar por estado'), 'PENDIENTE')

    const statusAlert = await screen.findByRole('status')
    expect(statusAlert).toHaveTextContent(/Error temporal del servidor/i)
    expect(screen.getByText('Pedido #21')).toBeInTheDocument()

    rerender(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/mis-pedidos']}>
          <MisPedidosPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )
  })

  it('pagina en servidor y reinicia skip=0 al cambiar el filtro de estado', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })

    const observedParams: Array<Record<string, unknown>> = []

    const adapter: AxiosAdapter = vi.fn(async (config) => {
      const params = (config.params ?? {}) as Record<string, unknown>
      observedParams.push({ ...params })

      if (params.estado === 'PENDIENTE') {
        return createAxiosResponse(config, 200, {
          total: 1,
          items: [makePedido({ id: 99, estado: 'PENDIENTE' })],
        } satisfies PedidosPaginados)
      }

      if (params.skip === 10) {
        return createAxiosResponse(config, 200, {
          total: 15,
          items: [makePedido({ id: 12, estado: 'ENTREGADO' })],
        } satisfies PedidosPaginados)
      }

      return createAxiosResponse(config, 200, {
        total: 15,
        items: [makePedido({ id: 11, estado: 'PENDIENTE' })],
      } satisfies PedidosPaginados)
    })

    axiosInstance.defaults.adapter = adapter
    renderWithProviders(<MisPedidosPage />)

    expect(await screen.findByText('Pedido #11')).toBeInTheDocument()
    expect(observedParams[0]).toEqual({ skip: 0, limit: 10 })

    // Avanzar a página 2 (skip = 10)
    await user.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(await screen.findByText('Pedido #12')).toBeInTheDocument()
    expect(observedParams.at(-1)).toEqual({ skip: 10, limit: 10 })

    // Aplicar filtro de estado debe reiniciar skip = 0
    await user.selectOptions(screen.getByLabelText('Filtrar por estado'), 'PENDIENTE')
    expect(await screen.findByText('Pedido #99')).toBeInTheDocument()
    expect(observedParams.at(-1)).toEqual({ skip: 0, limit: 10, estado: 'PENDIENTE' })
  })

  it('muestra botón Cancelar pedido solo en PENDIENTE (RN-04) y navega al detalle con líneas snapshot (RN-05)', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })

    const pedidoPendiente = makePedido({
      id: 10,
      estado: 'PENDIENTE',
      forma_pago: 'TRANSFERENCIA',
      direccion_entrega: 'San Martín 450',
      notas: null,
    })
    const pedidoEnPrep = makePedido({
      id: 11,
      estado: 'EN_PREPARACION',
    })

    const adapter: AxiosAdapter = vi.fn(async (config) => {
      if (config.url === '/pedidos') {
        return createAxiosResponse(config, 200, {
          total: 2,
          items: [pedidoPendiente, pedidoEnPrep],
        } satisfies PedidosPaginados)
      }
      if (config.url === '/pedidos/10') {
        return createAxiosResponse(config, 200, pedidoPendiente)
      }
      return createAxiosResponse(config, 404, { detail: 'No encontrado' })
    })

    axiosInstance.defaults.adapter = adapter

    renderWithProviders(
      <Routes>
        <Route path="/mis-pedidos" element={<MisPedidosPage />} />
        <Route path="/mis-pedidos/:id" element={<PedidoDetallePage />} />
      </Routes>,
    )

    expect(await screen.findByText('Pedido #10')).toBeInTheDocument()
    expect(screen.getByText('Pedido #11')).toBeInTheDocument()

    // Solo existe botón de cancelación para el pedido PENDIENTE (#10)
    expect(
      screen.getByRole('button', { name: 'Cancelar pedido #10' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Cancelar pedido #11' }),
    ).not.toBeInTheDocument()

    // Navegar al detalle del pedido #10
    await user.click(screen.getByRole('link', { name: 'Ver detalle del pedido #10' }))

    expect(await screen.findByRole('heading', { name: 'Pedido #10' })).toBeInTheDocument()
    expect(screen.getByText('San Martín 450')).toBeInTheDocument()
    expect(screen.getByText('Transferencia')).toBeInTheDocument()
    expect(screen.getByText('Sin notas adicionales')).toBeInTheDocument()

    // Verificar tabla de líneas snapshot (RN-05)
    const table = screen.getByRole('table')
    expect(within(table).getByText('Hamburguesa Clásica')).toBeInTheDocument()
    expect(within(table).getByText('Gaseosa Cola 500ml')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Volver a mis pedidos/i })).toHaveAttribute(
      'href',
      '/mis-pedidos',
    )
  })

  it('maneja error 400 en modal sin simular éxito y ante 200 invalida las 4 query keys y actualiza estado (RN-03)', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    let pedidoActual = makePedido({ id: 33, estado: 'PENDIENTE' })
    let patchAttempts = 0

    const adapter: AxiosAdapter = vi.fn(async (config) => {
      if (config.url === '/pedidos/33' && config.method === 'get') {
        return createAxiosResponse(config, 200, pedidoActual)
      }
      if (config.url === '/pedidos/33/cancelar' && config.method === 'patch') {
        patchAttempts += 1
        if (patchAttempts === 1) {
          throw createAxiosHttpError(config, 400, {
            detail: 'Solo se pueden cancelar pedidos en estado PENDIENTE',
          })
        }
        pedidoActual = makePedido({ id: 33, estado: 'CANCELADO' })
        return createAxiosResponse(config, 200, pedidoActual)
      }
      return createAxiosResponse(config, 404, { detail: 'No encontrado' })
    })

    axiosInstance.defaults.adapter = adapter

    renderWithProviders(
      <Routes>
        <Route path="/mis-pedidos/:id" element={<PedidoDetallePage />} />
      </Routes>,
      ['/mis-pedidos/33'],
    )

    expect(await screen.findByRole('heading', { name: 'Pedido #33' })).toBeInTheDocument()

    // Abrir modal accesible de cancelación
    await user.click(screen.getByRole('button', { name: 'Cancelar pedido' }))

    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')

    // Primer intento falla con 400 -> muestra role="alert" dentro del modal y mantiene PENDIENTE
    await user.click(within(dialog).getByRole('button', { name: 'Confirmar cancelación' }))

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(
      'Solo se pueden cancelar pedidos en estado PENDIENTE',
    )
    expect(screen.getByText('Pendiente')).toBeInTheDocument()

    // Segundo intento exitoso -> cierra modal, invalida 4 query keys y oculta botón cancelar
    await user.click(within(dialog).getByRole('button', { name: 'Confirmar cancelación' }))

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: PEDIDOS_QUERY_KEY })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: [...PEDIDOS_QUERY_KEY, 33] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: PEDIDOS_RESUMEN_QUERY_KEY })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: PRODUCTOS_ROOT_QUERY_KEY })

    expect(await screen.findByText('Cancelado')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Cancelar pedido' })).not.toBeInTheDocument()
  })
})
