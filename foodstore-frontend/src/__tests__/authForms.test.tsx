/**
 * Pruebas unitarias y de integración para validación, formularios de auth (`LoginPage`,
 * `RegisterPage`) y pantalla `UnauthorizedPage` (`E8.1`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - HU-TPI-01, tablas "Rutas y pantallas" y "Formularios" (págs. 18–20).
 */
import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
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

import {
  AUTH_VALIDATION_MESSAGES,
  LoginPage,
  RegisterPage,
  UnauthorizedPage,
  validateEmail,
  validateFullName,
  validatePassword,
  validateUsername,
  type UserPublic,
} from '@/features/auth'
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
  initialEntries: Array<string | { pathname: string; state?: unknown }> = ['/'],
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
  registerAuthInterceptorHandlers()
  useAuthStore.setState({ usuario: null, cargando: false, error: null })
})

afterEach(() => {
  axiosInstance.defaults.adapter = originalAdapter
  queryClient.clear()
  localStorage.clear()
  vi.restoreAllMocks()
})

describe('Validadores puros de authValidation con .trim()', () => {
  it('rechaza cadenas vacías o de solo espacios en todos los campos', () => {
    expect(validateUsername('   ')).toBe(AUTH_VALIDATION_MESSAGES.USERNAME_REQUIRED)
    expect(validateFullName('   ')).toBe(AUTH_VALIDATION_MESSAGES.FULL_NAME_REQUIRED)
    expect(validateEmail('   ')).toBe(AUTH_VALIDATION_MESSAGES.EMAIL_REQUIRED)
    expect(validatePassword('   ')).toBe(AUTH_VALIDATION_MESSAGES.PASSWORD_REQUIRED)
  })

  it('valida longitudes tras .trim() y límite de 72 bytes UTF-8 en password', () => {
    expect(validateUsername('  ana  ')).toBeUndefined()
    expect(validateUsername('a'.repeat(51))).toBe(AUTH_VALIDATION_MESSAGES.USERNAME_LENGTH)

    expect(validateFullName('  Ana Pérez  ')).toBeUndefined()
    expect(validateFullName('a'.repeat(151))).toBe(AUTH_VALIDATION_MESSAGES.FULL_NAME_LENGTH)

    expect(validatePassword('  short  ')).toBe(AUTH_VALIDATION_MESSAGES.PASSWORD_MIN_LENGTH)
    expect(validatePassword('a'.repeat(73))).toBe(AUTH_VALIDATION_MESSAGES.PASSWORD_MIN_LENGTH)
    // 20 emojis = 40 code units UTF-16 (<= 72), pero 80 bytes UTF-8 (> 72)
    expect(validatePassword('🚀'.repeat(20))).toBe(
      AUTH_VALIDATION_MESSAGES.PASSWORD_MAX_UTF8_BYTES,
    )
    expect(validatePassword('  ClaveSegura1  ')).toBeUndefined()
  })

  it('valida formato de correo electrónico tras .trim()', () => {
    expect(validateEmail('  cliente1@example.com  ')).toBeUndefined()
    expect(validateEmail('correo-invalido')).toBe(AUTH_VALIDATION_MESSAGES.EMAIL_INVALID)
  })
})

describe('LoginPage', () => {
  it('bloquea envío con campos vacíos y expone errores accesibles por campo', async () => {
    const user = userEvent.setup()
    let calls = 0
    axiosInstance.defaults.adapter = async () => {
      calls += 1
      throw new Error('No debería enviar solicitud HTTP')
    }

    renderWithProviders(<LoginPage />, ['/login'])

    await user.click(screen.getByRole('button', { name: 'Ingresar' }))

    const usernameInput = screen.getByLabelText('Nombre de usuario')
    const passwordInput = screen.getByLabelText('Contraseña')

    expect(calls).toBe(0)
    expect(usernameInput).toHaveAttribute('aria-invalid', 'true')
    expect(passwordInput).toHaveAttribute('aria-invalid', 'true')
    expect(usernameInput.getAttribute('aria-describedby')).toBeTruthy()
    expect(passwordInput.getAttribute('aria-describedby')).toBeTruthy()

    const alerts = screen.getAllByRole('alert')
    expect(alerts.map((el) => el.textContent)).toContain(
      AUTH_VALIDATION_MESSAGES.USERNAME_REQUIRED,
    )
    expect(alerts.map((el) => el.textContent)).toContain(
      AUTH_VALIDATION_MESSAGES.PASSWORD_REQUIRED,
    )
  })

  it('ante error HTTP 401/400 muestra alerta, conserva entradas y no autentica sesión', async () => {
    const user = userEvent.setup()
    const mockAdapter: AxiosAdapter = async (config) => {
      if (config.url === '/auth/token') {
        throw createAxiosHttpError(config, 401, { detail: 'Credenciales inválidas' })
      }
      throw new Error(`Unexpected URL: ${config.url}`)
    }
    axiosInstance.defaults.adapter = mockAdapter

    renderWithProviders(
      <>
        <LoginPage />
        <LocationProbe />
      </>,
      ['/login'],
    )

    const usernameInput = screen.getByLabelText('Nombre de usuario')
    const passwordInput = screen.getByLabelText('Contraseña')

    await user.type(usernameInput, 'cliente1')
    await user.type(passwordInput, 'ClaveErronea1')
    await user.click(screen.getByRole('button', { name: 'Ingresar' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Credenciales inválidas')
    })
    expect(usernameInput).toHaveValue('cliente1')
    expect(passwordInput).toHaveValue('ClaveErronea1')
    expect(useAuthStore.getState().usuario).toBeNull()
    expect(screen.getByTestId('current-path')).toHaveTextContent('/login')
  })

  it('envía form urlencoded, hidrata sesión y redirige a state.from o /', async () => {
    const user = userEvent.setup()
    let receivedBody = ''
    let receivedContentType = ''

    const mockAdapter: AxiosAdapter = async (config) => {
      if (config.url === '/auth/token') {
        receivedBody = String(config.data ?? '')
        receivedContentType = String(config.headers?.['Content-Type'] ?? '')
        return createAxiosResponse(config, 200, { message: 'Login exitoso' })
      }
      if (config.url === '/auth/me') {
        return createAxiosResponse(config, 200, USER_CLIENTE)
      }
      throw new Error(`Unexpected URL: ${config.url}`)
    }
    axiosInstance.defaults.adapter = mockAdapter

    renderWithProviders(
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/checkout" element={<h1>Confirmar pedido</h1>} />
      </Routes>,
      [{ pathname: '/login', state: { from: { pathname: '/checkout' } } }],
    )

    await user.type(screen.getByLabelText('Nombre de usuario'), '  cliente1  ')
    await user.type(screen.getByLabelText('Contraseña'), '  ClaveValida1  ')
    await user.click(screen.getByRole('button', { name: 'Ingresar' }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Confirmar pedido' })).toBeInTheDocument()
    })
    expect(receivedContentType).toContain('application/x-www-form-urlencoded')
    expect(receivedBody).toBe('username=cliente1&password=ClaveValida1')
    expect(useAuthStore.getState().usuario).toEqual(USER_CLIENTE)
  })
})

describe('RegisterPage', () => {
  it('ante 409 Conflict conserva las entradas y no confirma sesión inexistente', async () => {
    const user = userEvent.setup()
    const mockAdapter: AxiosAdapter = async (config) => {
      if (config.url === '/auth/register') {
        throw createAxiosHttpError(config, 409, {
          detail: 'El nombre de usuario o email ya está registrado',
        })
      }
      throw new Error(`Unexpected URL: ${config.url}`)
    }
    axiosInstance.defaults.adapter = mockAdapter

    renderWithProviders(<RegisterPage />, ['/register'])

    const usernameInput = screen.getByLabelText('Nombre de usuario')
    const fullNameInput = screen.getByLabelText('Nombre completo')
    const emailInput = screen.getByLabelText('Correo electrónico')
    const passwordInput = screen.getByLabelText('Contraseña')

    await user.type(usernameInput, 'cliente1')
    await user.type(fullNameInput, 'Cliente Uno')
    await user.type(emailInput, 'cliente1@example.com')
    await user.type(passwordInput, 'ClaveSegura1')
    await user.click(screen.getByRole('button', { name: 'Registrarse' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        'El nombre de usuario o email ya está registrado',
      )
    })
    expect(usernameInput).toHaveValue('cliente1')
    expect(fullNameInput).toHaveValue('Cliente Uno')
    expect(emailInput).toHaveValue('cliente1@example.com')
    expect(passwordInput).toHaveValue('ClaveSegura1')
    expect(useAuthStore.getState().usuario).toBeNull()
  })

  it('ante 201 Created normaliza con .trim() y redirige a /login con aviso de cuenta creada', async () => {
    const user = userEvent.setup()
    let postedPayload: unknown = null

    const mockAdapter: AxiosAdapter = async (config) => {
      if (config.url === '/auth/register') {
        postedPayload = JSON.parse(String(config.data))
        return createAxiosResponse(config, 201, USER_CLIENTE)
      }
      throw new Error(`Unexpected URL: ${config.url}`)
    }
    axiosInstance.defaults.adapter = mockAdapter

    renderWithProviders(<AppRoutes />, ['/register'])

    await user.type(screen.getByLabelText('Nombre de usuario'), '  cliente1  ')
    await user.type(screen.getByLabelText('Nombre completo'), '  Cliente Uno  ')
    await user.type(screen.getByLabelText('Correo electrónico'), '  cliente1@example.com  ')
    await user.type(screen.getByLabelText('Contraseña'), '  ClaveSegura1  ')
    await user.click(screen.getByRole('button', { name: 'Registrarse' }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    })
    expect(postedPayload).toEqual({
      username: 'cliente1',
      full_name: 'Cliente Uno',
      email: 'cliente1@example.com',
      password: 'ClaveSegura1',
    })
    expect(screen.getByRole('status')).toHaveTextContent('Cuenta creada para cliente1')
    expect(useAuthStore.getState().usuario).toBeNull()
  })
})

describe('UnauthorizedPage', () => {
  it('renderiza encabezado accesible y enlace hacia el catálogo /', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })

    renderWithProviders(
      <Routes>
        <Route path="/unauthorized" element={<UnauthorizedPage />} />
        <Route path="/" element={<h1>Food Store</h1>} />
      </Routes>,
      ['/unauthorized'],
    )

    expect(screen.getByRole('heading', { name: 'Acceso no autorizado' })).toBeInTheDocument()
    const homeLink = screen.getByRole('link', { name: 'Volver al catálogo' })
    expect(homeLink).toHaveAttribute('href', '/')

    await user.click(homeLink)
    expect(screen.getByRole('heading', { name: 'Food Store' })).toBeInTheDocument()
  })
})
