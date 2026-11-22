/**
 * Pruebas unitarias y de integración para `AdminUsuariosPage`, `UsuariosTable`, `useUsuarios` y `usuariosApi` (`E9.4`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Historia `HU-TPI-06` y ruta `/admin/usuarios` (págs. 12, 17–20).
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

import { AdminUsuariosPage, type UserPublic } from '@/features/usuarios'
import { AppRoutes } from '@/routes/AppRouter'
import { axiosInstance } from '@/shared/api/axiosInstance'
import { queryClient } from '@/shared/api/queryClient'
import { registerAuthInterceptorHandlers, useAuthStore } from '@/store/authStore'

const originalAdapter = axiosInstance.defaults.adapter

const USER_ADMIN: UserPublic = {
  id: 1,
  username: 'admin',
  full_name: 'Administrador Principal',
  email: 'admin@example.com',
  role: 'admin',
  disabled: false,
  created_at: '2026-11-20T12:00:00Z',
}

const USER_ACTIVO: UserPublic = {
  id: 2,
  username: 'carlos',
  full_name: 'Carlos Pérez',
  email: 'carlos@example.com',
  role: 'user',
  disabled: false,
  created_at: '2026-11-20T12:05:00Z',
}

const USER_DESACTIVADO: UserPublic = {
  id: 3,
  username: 'ana',
  full_name: 'Ana Gómez',
  email: 'ana@example.com',
  role: 'user',
  disabled: true,
  created_at: '2026-11-20T12:10:00Z',
}

const SAMPLE_USUARIOS: UserPublic[] = [USER_ADMIN, USER_ACTIVO, USER_DESACTIVADO]

function makeUsuario(id: number, overrides: Partial<UserPublic> = {}): UserPublic {
  return {
    id,
    username: `usuario${String(id).padStart(2, '0')}`,
    full_name: `Usuario ${String(id).padStart(2, '0')}`,
    email: `usuario${id}@example.com`,
    role: id === 1 ? 'admin' : 'user',
    disabled: false,
    created_at: '2026-11-20T12:00:00Z',
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

function renderWithProviders(ui: ReactNode, initialEntries: string[] = ['/admin/usuarios']) {
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

describe('AdminUsuariosPage (E9.4)', () => {
  it('redirige a /login sin sesión y a /unauthorized para rol user en /admin/usuarios', async () => {
    const firstRender = renderWithProviders(
      <>
        <AppRoutes />
        <LocationProbe />
      </>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('current-path')).toHaveTextContent('/login')
    })

    firstRender.unmount()

    useAuthStore.setState({ usuario: USER_ACTIVO, cargando: false, error: null })
    renderWithProviders(
      <>
        <AppRoutes />
        <LocationProbe />
      </>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('current-path')).toHaveTextContent('/unauthorized')
    })
  })

  it('renderiza tabla semántica, oculta Desactivar en la fila del usuario logueado y muestra Activar/Desactivar según estado', async () => {
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })

    const adapterSpy = vi.fn<AxiosAdapter>(async (config) => {
      if (config.method === 'get' && config.url === '/admin/usuarios') {
        expect(config.params).toBeUndefined()
        return createAxiosResponse(config, 200, SAMPLE_USUARIOS)
      }
      throw new Error(`Unexpected request: ${config.method} ${config.url}`)
    })
    axiosInstance.defaults.adapter = adapterSpy

    renderWithProviders(<AdminUsuariosPage />)

    const table = await screen.findByRole('table')
    const headers = within(table).getAllByRole('columnheader')
    expect(headers).toHaveLength(7)
    for (const header of headers) {
      expect(header).toHaveAttribute('scope', 'col')
    }

    const rowAdmin = within(table).getByText('admin').closest('tr')!
    expect(within(rowAdmin).getByText('Administrador Principal')).toBeInTheDocument()
    expect(within(rowAdmin).getByText('Activo')).toBeInTheDocument()
    expect(within(rowAdmin).getByText('Sesión actual')).toBeInTheDocument()
    expect(within(rowAdmin).queryByRole('button', { name: 'Desactivar' })).not.toBeInTheDocument()
    expect(within(rowAdmin).queryByRole('button', { name: 'Activar' })).not.toBeInTheDocument()

    const rowCarlos = within(table).getByText('carlos').closest('tr')!
    expect(within(rowCarlos).getByText('Activo')).toBeInTheDocument()
    expect(within(rowCarlos).getByRole('button', { name: 'Desactivar' })).toBeInTheDocument()

    const rowAna = within(table).getByText('ana').closest('tr')!
    expect(within(rowAna).getByText('Desactivado')).toBeInTheDocument()
    expect(within(rowAna).getByRole('button', { name: 'Activar' })).toBeInTheDocument()
  })

  it('ejecuta desactivar y activar con estado de carga e invalida la consulta [' + "'usuarios', 'admin'" + ']', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })

    let usuariosDb: UserPublic[] = SAMPLE_USUARIOS.map((u) => ({ ...u }))
    let resolveMutation: ((value: AxiosResponse) => void) | null = null

    const adapterSpy = vi.fn<AxiosAdapter>(async (config) => {
      if (config.method === 'get' && config.url === '/admin/usuarios') {
        return createAxiosResponse(
          config,
          200,
          usuariosDb.map((u) => ({ ...u })),
        )
      }
      if (config.method === 'post' && config.url === '/admin/usuarios/2/desactivar') {
        return new Promise<AxiosResponse>((resolve) => {
          resolveMutation = (res) => resolve(res)
          usuariosDb = usuariosDb.map((u) => (u.id === 2 ? { ...u, disabled: true } : u))
        })
      }
      if (config.method === 'post' && config.url === '/admin/usuarios/3/activar') {
        usuariosDb = usuariosDb.map((u) => (u.id === 3 ? { ...u, disabled: false } : u))
        const updated = usuariosDb.find((u) => u.id === 3)!
        return createAxiosResponse(config, 200, updated)
      }
      throw new Error(`Unexpected request: ${config.method} ${config.url}`)
    })
    axiosInstance.defaults.adapter = adapterSpy

    renderWithProviders(<AdminUsuariosPage />)

    const table = await screen.findByRole('table')
    const rowCarlos = within(table).getByText('carlos').closest('tr')!
    const desactivarBtn = within(rowCarlos).getByRole('button', { name: 'Desactivar' })

    const clickPromise = user.click(desactivarBtn)

    await waitFor(() => {
      const busyBtn = within(rowCarlos).getByRole('button', { name: 'Desactivando…' })
      expect(busyBtn).toBeDisabled()
      expect(busyBtn).toHaveAttribute('aria-busy', 'true')
    })

    const updatedCarlos = usuariosDb.find((u) => u.id === 2)!
    resolveMutation!(createAxiosResponse({} as InternalAxiosRequestConfig, 200, updatedCarlos))
    await clickPromise

    await waitFor(() => {
      const updatedRowCarlos = within(table).getByText('carlos').closest('tr')!
      expect(within(updatedRowCarlos).getByText('Desactivado')).toBeInTheDocument()
      expect(within(updatedRowCarlos).getByRole('button', { name: 'Activar' })).toBeInTheDocument()
    })

    const rowAna = within(table).getByText('ana').closest('tr')!
    await user.click(within(rowAna).getByRole('button', { name: 'Activar' }))

    await waitFor(() => {
      const updatedRowAna = within(table).getByText('ana').closest('tr')!
      expect(within(updatedRowAna).getByText('Activo')).toBeInTheDocument()
      expect(within(updatedRowAna).getByRole('button', { name: 'Desactivar' })).toBeInTheDocument()
    })

    const getCalls = adapterSpy.mock.calls.filter(
      ([cfg]) => cfg.method === 'get' && cfg.url === '/admin/usuarios',
    )
    expect(getCalls.length).toBeGreaterThanOrEqual(3)
  })

  it('muestra error role="alert" y conserva el usuario y su estado confirmado ante fallo 400 o 404', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })

    const adapterSpy = vi.fn<AxiosAdapter>(async (config) => {
      if (config.method === 'get' && config.url === '/admin/usuarios') {
        return createAxiosResponse(config, 200, SAMPLE_USUARIOS)
      }
      if (config.method === 'post' && config.url === '/admin/usuarios/2/desactivar') {
        throw createAxiosHttpError(config, 400, {
          detail: 'No podés desactivar tu propia cuenta',
        })
      }
      if (config.method === 'post' && config.url === '/admin/usuarios/3/activar') {
        throw createAxiosHttpError(config, 404, {
          detail: 'Usuario no encontrado',
        })
      }
      throw new Error(`Unexpected request: ${config.method} ${config.url}`)
    })
    axiosInstance.defaults.adapter = adapterSpy

    renderWithProviders(<AdminUsuariosPage />)

    const table = await screen.findByRole('table')
    const rowCarlos = within(table).getByText('carlos').closest('tr')!
    await user.click(within(rowCarlos).getByRole('button', { name: 'Desactivar' }))

    const alert400 = await screen.findByRole('alert')
    expect(alert400).toHaveTextContent('No podés desactivar tu propia cuenta')
    expect(within(rowCarlos).getByText('Activo')).toBeInTheDocument()
    expect(within(rowCarlos).getByRole('button', { name: 'Desactivar' })).toBeInTheDocument()

    const rowAna = within(table).getByText('ana').closest('tr')!
    await user.click(within(rowAna).getByRole('button', { name: 'Activar' }))

    const alert404 = await screen.findByRole('alert')
    expect(alert404).toHaveTextContent('Usuario no encontrado')
    expect(within(rowAna).getByText('Desactivado')).toBeInTheDocument()
    expect(within(rowAna).getByRole('button', { name: 'Activar' })).toBeInTheDocument()
  })

  it('soporta ordenamiento con aria-sort y resetea paginación a pageIndex 0 al filtrar', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })

    const manyUsers: UserPublic[] = Array.from({ length: 12 }, (_, idx) => makeUsuario(idx + 1))

    axiosInstance.defaults.adapter = vi.fn<AxiosAdapter>(async (config) => {
      if (config.method === 'get' && config.url === '/admin/usuarios') {
        return createAxiosResponse(config, 200, manyUsers)
      }
      throw new Error(`Unexpected request: ${config.method} ${config.url}`)
    })

    renderWithProviders(<AdminUsuariosPage />)

    await screen.findByText('Página 1 de 2 (12 usuarios)')

    const usernameHeader = screen.getByRole('columnheader', { name: /Usuario/i })
    expect(usernameHeader).toHaveAttribute('aria-sort', 'none')
    const sortButton = within(usernameHeader).getByRole('button', { name: /Usuario/i })

    await user.click(sortButton)
    expect(usernameHeader).toHaveAttribute('aria-sort', 'ascending')

    await user.click(sortButton)
    expect(usernameHeader).toHaveAttribute('aria-sort', 'descending')

    await user.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(screen.getByText('Página 2 de 2 (12 usuarios)')).toBeInTheDocument()

    const searchInput = screen.getByLabelText('Buscar usuario')
    await user.type(searchInput, 'usuario01')

    expect(screen.getByText('Página 1 de 1 (1 usuarios)')).toBeInTheDocument()
    expect(screen.getByText('usuario01')).toBeInTheDocument()
  })

  it('conserva datos previos y muestra aviso inline-refetch cuando falla la recarga', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })

    let shouldFailRefetch = false
    axiosInstance.defaults.adapter = vi.fn<AxiosAdapter>(async (config) => {
      if (config.method === 'get' && config.url === '/admin/usuarios') {
        if (shouldFailRefetch) {
          throw createAxiosHttpError(config, 500, { detail: 'Fallo temporal de red' })
        }
        return createAxiosResponse(config, 200, SAMPLE_USUARIOS)
      }
      throw new Error(`Unexpected request: ${config.method} ${config.url}`)
    })

    renderWithProviders(<AdminUsuariosPage />)

    await screen.findByText('carlos')

    shouldFailRefetch = true
    await queryClient.invalidateQueries({ queryKey: ['usuarios', 'admin'] })

    const statusBanner = await screen.findByRole('status')
    expect(statusBanner).toHaveTextContent(
      'No se pudieron actualizar los usuarios; se conservan los últimos datos confirmados.',
    )
    expect(screen.getByText('carlos')).toBeInTheDocument()
    expect(screen.getByText('ana')).toBeInTheDocument()

    shouldFailRefetch = false
    await user.click(within(statusBanner).getByRole('button', { name: 'Reintentar' }))

    await waitFor(() => {
      expect(screen.queryByRole('status')).not.toBeInTheDocument()
    })
  })
})
