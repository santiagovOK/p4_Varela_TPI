import { render, screen, waitFor } from '@testing-library/react'
import {
  AxiosError,
  AxiosHeaders,
  type AxiosAdapter,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { App } from '@/App'
import type { UserPublic } from '@/features/auth'
import { AppRoutes } from '@/routes/AppRouter'
import { ProtectedRoute } from '@/routes/ProtectedRoute'
import {
  axiosInstance,
  setAuthGenerationGetter,
  setUnauthorizedHandler,
} from '@/shared/api/axiosInstance'
import { queryClient } from '@/shared/api/queryClient'
import {
  AUTH_STORAGE_KEY,
  registerAuthInterceptorHandlers,
  useAuthStore,
} from '@/store/authStore'

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

const USER_ADMIN: UserPublic = {
  id: 1,
  username: 'admin',
  full_name: 'Administrador',
  email: 'admin@example.com',
  role: 'admin',
  disabled: false,
  created_at: '2026-11-20T12:00:00Z',
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

function LocationDisplay({ testId }: { testId: string }) {
  const location = useLocation()
  return (
    <div data-testid={testId}>
      {location.pathname}
      {location.state && typeof location.state === 'object' && 'from' in location.state
        ? `|from:${(location.state as { from: { pathname: string } }).from.pathname}`
        : ''}
    </div>
  )
}

beforeEach(() => {
  localStorage.clear()
  queryClient.clear()
  registerAuthInterceptorHandlers()
  useAuthStore.getState().clearSession()
})

afterEach(() => {
  axiosInstance.defaults.adapter = originalAdapter
  setUnauthorizedHandler(null)
  setAuthGenerationGetter(null)
  queryClient.clear()
  localStorage.clear()
  vi.restoreAllMocks()
})

describe('authStore, AuthProvider, ProtectedRoute y AppRouter', () => {
  it('persiste únicamente usuario en localStorage mediante partialize (nunca JWT ni cargando)', async () => {
    const mockAdapter: AxiosAdapter = async (config) => {
      if (config.url === '/auth/token') {
        return createAxiosResponse(config, 200, {
          message: 'Login exitoso',
          access_token: 'jwt-no-persistir',
        })
      }
      if (config.url === '/auth/me') {
        return createAxiosResponse(config, 200, USER_CLIENTE)
      }
      throw new Error(`Unexpected URL: ${config.url}`)
    }
    axiosInstance.defaults.adapter = mockAdapter

    await useAuthStore.getState().login('cliente1', 'Password123!')

    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    expect(raw).not.toBeNull()
    const parsed = JSON.parse(raw!) as { state: Record<string, unknown>; version: number }

    expect(parsed.state).toEqual({ usuario: USER_CLIENTE })
    expect(parsed.state).not.toHaveProperty('cargando')
    expect(parsed.state).not.toHaveProperty('error')
    expect(raw).not.toContain('jwt-no-persistir')
  })

  it('login envía formulario x-www-form-urlencoded a /auth/token, hidrata con /auth/me y limpia queryClient', async () => {
    const clearSpy = vi.spyOn(queryClient, 'clear')
    let capturedContentType: string | undefined
    let capturedBody = ''

    const mockAdapter: AxiosAdapter = async (config) => {
      if (config.url === '/auth/token') {
        const headers = AxiosHeaders.from(config.headers)
        capturedContentType = String(headers.getContentType() ?? headers.get('Content-Type'))
        capturedBody = config.data instanceof URLSearchParams ? config.data.toString() : String(config.data)
        return createAxiosResponse(config, 200, { message: 'Login exitoso' })
      }
      if (config.url === '/auth/me') {
        return createAxiosResponse(config, 200, USER_ADMIN)
      }
      throw new Error(`Unexpected URL: ${config.url}`)
    }
    axiosInstance.defaults.adapter = mockAdapter

    const user = await useAuthStore.getState().login('admin', 'Admin1234!')

    expect(capturedContentType).toContain('application/x-www-form-urlencoded')
    expect(capturedBody).toBe('username=admin&password=Admin1234%21')
    expect(user).toEqual(USER_ADMIN)
    expect(useAuthStore.getState().usuario).toEqual(USER_ADMIN)
    expect(useAuthStore.getState().cargando).toBe(false)
    expect(clearSpy).toHaveBeenCalledTimes(1)
  })

  it('login preserva error.cause ante 401/400 sin activar clearSession global por /auth/token', async () => {
    const clearSpy = vi.spyOn(useAuthStore.getState(), 'clearSession')

    const mockAdapter: AxiosAdapter = async (config) => {
      throw createAxiosHttpError(config, 401, { detail: 'Credenciales inválidas' })
    }
    axiosInstance.defaults.adapter = mockAdapter

    await expect(useAuthStore.getState().login('admin', 'wrong')).rejects.toMatchObject({
      message: 'Credenciales inválidas',
    })

    const state = useAuthStore.getState()
    expect(state.cargando).toBe(false)
    expect(state.error).toBeInstanceOf(Error)
    expect(state.error?.cause).toBeInstanceOf(AxiosError)
    expect(clearSpy).not.toHaveBeenCalled()
  })

  it('deduplica llamadas concurrentes a checkSession mediante activeCheck', async () => {
    let meCalls = 0
    let resolveRequest: ((value: AxiosResponse) => void) | undefined

    const mockAdapter: AxiosAdapter = (config) => {
      if (config.url === '/auth/me') {
        meCalls += 1
        return new Promise<AxiosResponse>((resolve) => {
          resolveRequest = resolve
        })
      }
      return Promise.reject(new Error(`Unexpected URL: ${config.url}`))
    }
    axiosInstance.defaults.adapter = mockAdapter

    const p1 = useAuthStore.getState().checkSession()
    const p2 = useAuthStore.getState().checkSession()

    expect(p1).toBe(p2)
    await waitFor(() => {
      expect(meCalls).toBe(1)
    })

    resolveRequest?.(createAxiosResponse({ headers: new AxiosHeaders() } as InternalAxiosRequestConfig, 200, USER_CLIENTE))
    await Promise.all([p1, p2])

    expect(useAuthStore.getState().usuario).toEqual(USER_CLIENTE)
    expect(useAuthStore.getState().cargando).toBe(false)
  })

  it('ejecuta queryClient.clear() cuando checkSession detecta cambio de identidad o 401/400 desactivada', async () => {
    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: true, error: null })
    queryClient.setQueryData(['pedidos'], [{ id: 99 }])

    const mockAdapter: AxiosAdapter = async (config) => {
      if (config.url === '/auth/me') {
        return createAxiosResponse(config, 200, USER_ADMIN)
      }
      throw new Error(`Unexpected URL: ${config.url}`)
    }
    axiosInstance.defaults.adapter = mockAdapter

    await useAuthStore.getState().checkSession()

    expect(useAuthStore.getState().usuario).toEqual(USER_ADMIN)
    expect(queryClient.getQueryData(['pedidos'])).toBeUndefined()

    queryClient.setQueryData(['pedidos'], [{ id: 100 }])
    axiosInstance.defaults.adapter = async (config) => {
      throw createAxiosHttpError(config, 400, { detail: 'Cuenta de usuario desactivada' })
    }

    await useAuthStore.getState().checkSession()

    expect(useAuthStore.getState().usuario).toBeNull()
    expect(useAuthStore.getState().cargando).toBe(false)
    expect(queryClient.getQueryData(['pedidos'])).toBeUndefined()
  })

  it('descarta respuestas tardías de checkSession cuando authGeneration cambió por logout/clearSession', async () => {
    let resolveDelayed: ((value: AxiosResponse) => void) | undefined

    const mockAdapter: AxiosAdapter = (config) => {
      if (config.url === '/auth/me') {
        return new Promise<AxiosResponse>((resolve) => {
          resolveDelayed = resolve
        })
      }
      if (config.url === '/auth/logout') {
        return Promise.resolve(createAxiosResponse(config, 200, { message: 'Logout exitoso' }))
      }
      return Promise.reject(new Error(`Unexpected URL: ${config.url}`))
    }
    axiosInstance.defaults.adapter = mockAdapter

    const checkPromise = useAuthStore.getState().checkSession()
    await useAuthStore.getState().logout()

    resolveDelayed?.(
      createAxiosResponse({ headers: new AxiosHeaders() } as InternalAxiosRequestConfig, 200, USER_ADMIN),
    )
    await checkPromise

    expect(useAuthStore.getState().usuario).toBeNull()
    expect(useAuthStore.getState().cargando).toBe(false)
  })

  it('logout limpia usuario, cargando y queryClient en try/finally aun si falla POST /auth/logout', async () => {
    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })
    queryClient.setQueryData(['productos'], [{ id: 1 }])

    axiosInstance.defaults.adapter = async (config) => {
      throw createAxiosHttpError(config, 500, { detail: 'Error interno' })
    }

    await expect(useAuthStore.getState().logout()).rejects.toMatchObject({
      message: 'Error interno',
    })

    expect(useAuthStore.getState().usuario).toBeNull()
    expect(useAuthStore.getState().cargando).toBe(false)
    expect(queryClient.getQueryData(['productos'])).toBeUndefined()
  })

  it('wiring con axiosInstance: limpia sesión en 401 y 400 desactivada, pero nunca en 403 Forbidden', async () => {
    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })
    queryClient.setQueryData(['pedidos'], [{ id: 1 }])

    // 403 nunca limpia sesión
    axiosInstance.defaults.adapter = async (config) => {
      throw createAxiosHttpError(config, 403, { detail: 'Permisos insuficientes' })
    }
    await expect(axiosInstance.get('/admin/usuarios')).rejects.toBeInstanceOf(Error)
    expect(useAuthStore.getState().usuario).toEqual(USER_CLIENTE)
    expect(queryClient.getQueryData(['pedidos'])).toBeDefined()

    // 401 en ruta protegida dispara clearSession
    axiosInstance.defaults.adapter = async (config) => {
      throw createAxiosHttpError(config, 401, { detail: 'No autenticado' })
    }
    await expect(axiosInstance.get('/pedidos')).rejects.toBeInstanceOf(Error)
    expect(useAuthStore.getState().usuario).toBeNull()
    expect(queryClient.getQueryData(['pedidos'])).toBeUndefined()

    // 400 Cuenta de usuario desactivada fuera de /auth/token dispara clearSession
    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })
    axiosInstance.defaults.adapter = async (config) => {
      throw createAxiosHttpError(config, 400, { detail: 'Cuenta de usuario desactivada' })
    }
    await expect(axiosInstance.get('/pedidos')).rejects.toBeInstanceOf(Error)
    expect(useAuthStore.getState().usuario).toBeNull()
  })

  it('ProtectedRoute espera cargando, redirige a /login con state.from, valida allowedRoles y renderiza Outlet', () => {
    // 1) cargando === true -> indicador accesible sin redirigir
    useAuthStore.setState({ usuario: null, cargando: true, error: null })
    const r1 = render(
      <MemoryRouter initialEntries={['/checkout']}>
        <AppRoutes />
      </MemoryRouter>,
    )
    expect(screen.getByRole('status')).toHaveTextContent('Verificando sesión…')
    r1.unmount()

    // 2) !usuario -> /login preservando state.from
    useAuthStore.setState({ usuario: null, cargando: false, error: null })
    const r2 = render(
      <MemoryRouter initialEntries={['/checkout']}>
        <Routes>
          <Route path="/login" element={<LocationDisplay testId="location" />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/checkout" element={<div>Checkout privado</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByTestId('location')).toHaveTextContent('/login|from:/checkout')
    r2.unmount()

    // 3) rol insuficiente -> /unauthorized
    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })
    const r3 = render(
      <MemoryRouter initialEntries={['/admin/usuarios']}>
        <AppRoutes />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: 'Acceso no autorizado' })).toBeInTheDocument()
    r3.unmount()

    // 4) rol permitido -> renderiza <Outlet />
    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })
    render(
      <MemoryRouter initialEntries={['/admin/usuarios']}>
        <AppRoutes />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: 'Gestión de usuarios' })).toBeInTheDocument()
  })

  it('AuthProvider dispara checkSession() automáticamente al montar App', async () => {
    let meCalls = 0
    axiosInstance.defaults.adapter = async (config) => {
      if (config.url === '/auth/me') {
        meCalls += 1
        return createAxiosResponse(config, 200, USER_CLIENTE)
      }
      throw new Error(`Unexpected URL: ${config.url}`)
    }

    window.history.pushState({}, '', '/')
    render(<App />)

    await waitFor(() => {
      expect(meCalls).toBe(1)
      expect(useAuthStore.getState().usuario).toEqual(USER_CLIENTE)
      expect(useAuthStore.getState().cargando).toBe(false)
    })
  })
})
