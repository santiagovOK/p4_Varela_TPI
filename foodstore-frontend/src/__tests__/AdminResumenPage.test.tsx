/**
 * Pruebas unitarias y de integración para `AdminResumenPage`, `ResumenCard` y `useResumenPedidos` (`E9.1`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Historia `HU-TPI-05`, ruta `/admin/resumen` y endpoint `GET /pedidos/resumen` (págs. 14, 18–20).
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
import { AdminResumenPage, type ResumenPedidos } from '@/features/pedidos'
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

const RESUMEN_SAMPLE: ResumenPedidos = {
  pendientes: 4,
  en_preparacion: 2,
  entregados: 15,
  cancelados: 1,
  pedidos_hoy: 7,
  ingresos_entregados: 124500.5,
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

function renderWithProviders(ui: ReactNode, initialEntries: string[] = ['/admin/resumen']) {
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

describe('AdminResumenPage (E9.1)', () => {
  it('redirige a /login cuando no hay sesión activa en /admin/resumen', async () => {
    renderWithProviders(
      <>
        <AppRoutes />
        <LocationProbe />
      </>,
      ['/admin/resumen'],
    )

    await waitFor(() => {
      expect(screen.getByTestId('current-path')).toHaveTextContent('/login')
    })
  })

  it('redirige a /unauthorized cuando un usuario con rol user intenta acceder a /admin/resumen', async () => {
    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })

    renderWithProviders(
      <>
        <AppRoutes />
        <LocationProbe />
      </>,
      ['/admin/resumen'],
    )

    await waitFor(() => {
      expect(screen.getByTestId('current-path')).toHaveTextContent('/unauthorized')
    })
    expect(screen.getByRole('heading', { name: /acceso no autorizado/i })).toBeInTheDocument()
  })

  it('muestra Skeleton accesible durante la carga inicial sin datos', async () => {
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })

    let resolveRequest: ((value: AxiosResponse) => void) | undefined
    const adapter: AxiosAdapter = (config) =>
      new Promise<AxiosResponse>((resolve) => {
        resolveRequest = resolve
        void config
      })
    axiosInstance.defaults.adapter = adapter

    renderWithProviders(<AdminResumenPage />)

    const loadingStatus = screen.getByRole('status')
    expect(loadingStatus).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByText(/cargando resumen de pedidos/i)).toBeInTheDocument()

    await waitFor(() => {
      expect(resolveRequest).toBeDefined()
    })
    resolveRequest?.(createAxiosResponse({} as InternalAxiosRequestConfig, 200, RESUMEN_SAMPLE))

    await waitFor(() => {
      expect(screen.getByTestId('resumen-card-pendientes')).toBeInTheDocument()
    })
  })

  it('renderiza los 6 indicadores de ResumenPedidos para rol admin con ingresos formateados', async () => {
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })

    const adapter = vi.fn<AxiosAdapter>(async (config) => {
      if (config.url === '/pedidos/resumen' && config.method?.toLowerCase() === 'get') {
        return createAxiosResponse(config, 200, RESUMEN_SAMPLE)
      }
      throw createAxiosHttpError(config, 404, { detail: 'No encontrado' })
    })
    axiosInstance.defaults.adapter = adapter

    renderWithProviders(
      <>
        <AppRoutes />
        <LocationProbe />
      </>,
      ['/admin/resumen'],
    )

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /resumen administrativo/i })).toBeInTheDocument()
      expect(screen.getByTestId('resumen-card-pendientes')).toBeInTheDocument()
    })

    expect(screen.getByTestId('current-path')).toHaveTextContent('/admin/resumen')
    expect(within(screen.getByTestId('resumen-card-pendientes')).getByText('4')).toBeInTheDocument()
    expect(
      within(screen.getByTestId('resumen-card-en_preparacion')).getByText('2'),
    ).toBeInTheDocument()
    expect(within(screen.getByTestId('resumen-card-entregados')).getByText('15')).toBeInTheDocument()
    expect(within(screen.getByTestId('resumen-card-cancelados')).getByText('1')).toBeInTheDocument()
    expect(within(screen.getByTestId('resumen-card-pedidos_hoy')).getByText('7')).toBeInTheDocument()
    expect(
      within(screen.getByTestId('resumen-card-ingresos_entregados')).getByText(/\$\s*124\.500,50/),
    ).toBeInTheDocument()
  })

  it('muestra EstadoError inicial con botón Reintentar y recupera los indicadores al reintentar', async () => {
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })
    const user = userEvent.setup()

    let attempt = 0
    const adapter = vi.fn<AxiosAdapter>(async (config) => {
      if (config.url === '/pedidos/resumen') {
        attempt += 1
        if (attempt === 1) {
          throw createAxiosHttpError(config, 500, { detail: 'Error interno al calcular resumen' })
        }
        return createAxiosResponse(config, 200, RESUMEN_SAMPLE)
      }
      throw createAxiosHttpError(config, 404, { detail: 'No encontrado' })
    })
    axiosInstance.defaults.adapter = adapter

    renderWithProviders(<AdminResumenPage />)

    const alert = await screen.findByRole('alert')
    expect(within(alert).getByText(/no se pudo cargar el resumen de pedidos/i)).toBeInTheDocument()
    expect(within(alert).getByText(/error interno al calcular resumen/i)).toBeInTheDocument()

    await user.click(within(alert).getByRole('button', { name: /reintentar/i }))

    await waitFor(() => {
      expect(screen.getByTestId('resumen-card-ingresos_entregados')).toBeInTheDocument()
    })
    expect(attempt).toBe(2)
  })

  it('conserva las 6 tarjetas previas y muestra aviso inline-refetch si falla la actualización', async () => {
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })
    const user = userEvent.setup()

    let attempt = 0
    const adapter = vi.fn<AxiosAdapter>(async (config) => {
      if (config.url === '/pedidos/resumen') {
        attempt += 1
        if (attempt === 1) {
          return createAxiosResponse(config, 200, RESUMEN_SAMPLE)
        }
        throw createAxiosHttpError(config, 503, { detail: 'Servicio temporalmente no disponible' })
      }
      throw createAxiosHttpError(config, 404, { detail: 'No encontrado' })
    })
    axiosInstance.defaults.adapter = adapter

    renderWithProviders(<AdminResumenPage />)

    await waitFor(() => {
      expect(screen.getByTestId('resumen-card-pendientes')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /actualizar/i }))

    const refetchStatus = await screen.findByRole('status')
    expect(
      within(refetchStatus).getByText(/se conservan los últimos valores confirmados/i),
    ).toBeInTheDocument()
    expect(
      within(refetchStatus).getByText(/servicio temporalmente no disponible/i),
    ).toBeInTheDocument()

    // Las 6 tarjetas con los últimos datos confirmados permanecen visibles
    expect(within(screen.getByTestId('resumen-card-pendientes')).getByText('4')).toBeInTheDocument()
    expect(
      within(screen.getByTestId('resumen-card-en_preparacion')).getByText('2'),
    ).toBeInTheDocument()
    expect(within(screen.getByTestId('resumen-card-entregados')).getByText('15')).toBeInTheDocument()
    expect(within(screen.getByTestId('resumen-card-cancelados')).getByText('1')).toBeInTheDocument()
    expect(within(screen.getByTestId('resumen-card-pedidos_hoy')).getByText('7')).toBeInTheDocument()
    expect(
      within(screen.getByTestId('resumen-card-ingresos_entregados')).getByText(/\$\s*124\.500,50/),
    ).toBeInTheDocument()
  })
})
