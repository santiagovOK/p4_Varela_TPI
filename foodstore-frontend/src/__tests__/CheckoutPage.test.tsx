/**
 * Pruebas unitarias y de integración para `checkoutValidation`, `CarritoPage` y `CheckoutPage` (`E8.3`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Reglas `RN-01`, `RN-05`, `RN-06` y `HU-TPI-03` (págs. 5, 13–14, 18–20).
 */
import { QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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
  CHECKOUT_VALIDATION_MESSAGES,
  CarritoPage,
  CheckoutPage,
  validateDireccionEntrega,
  validateFormaPago,
  validateNotas,
  type PedidoCreate,
  type PedidoRead,
} from '@/features/pedidos'
import { AppRoutes } from '@/routes/AppRouter'
import { axiosInstance } from '@/shared/api/axiosInstance'
import { queryClient } from '@/shared/api/queryClient'
import { registerAuthInterceptorHandlers, useAuthStore } from '@/store/authStore'
import { useCartStore } from '@/store/cartStore'

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

function seedCart() {
  useCartStore.setState({
    items: [
      {
        producto_id: 1,
        nombre: 'Hamburguesa Clásica',
        precio_unitario: 6500,
        cantidad: 2,
      },
      {
        producto_id: 3,
        nombre: 'Gaseosa Cola 500ml',
        precio_unitario: 1800,
        cantidad: 1,
      },
    ],
  })
}

beforeEach(() => {
  localStorage.clear()
  queryClient.clear()
  registerAuthInterceptorHandlers()
  useAuthStore.setState({ usuario: null, cargando: false, error: null })
  useCartStore.setState({ items: [] })
})

afterEach(() => {
  axiosInstance.defaults.adapter = originalAdapter
  queryClient.clear()
  localStorage.clear()
  vi.restoreAllMocks()
})

describe('Validadores puros de checkoutValidation con .trim()', () => {
  it('rechaza dirección vacía, solo espacios o fuera de rango 5–200 tras .trim()', () => {
    expect(validateDireccionEntrega('')).toBe(CHECKOUT_VALIDATION_MESSAGES.DIRECCION_REQUIRED)
    expect(validateDireccionEntrega('     ')).toBe(
      CHECKOUT_VALIDATION_MESSAGES.DIRECCION_REQUIRED,
    )
    expect(validateDireccionEntrega('  abc  ')).toBe(
      CHECKOUT_VALIDATION_MESSAGES.DIRECCION_LENGTH,
    )
    expect(validateDireccionEntrega('a'.repeat(201))).toBe(
      CHECKOUT_VALIDATION_MESSAGES.DIRECCION_LENGTH,
    )
    expect(validateDireccionEntrega('  Av. Siempre Viva 742  ')).toBeUndefined()
  })

  it('valida forma de pago y notas opcionales hasta 500 caracteres tras .trim()', () => {
    expect(validateFormaPago('EFECTIVO')).toBeUndefined()
    expect(validateFormaPago('TRANSFERENCIA')).toBeUndefined()
    expect(validateFormaPago('TARJETA')).toBe(CHECKOUT_VALIDATION_MESSAGES.FORMA_PAGO_INVALID)

    expect(validateNotas('')).toBeUndefined()
    expect(validateNotas('   ')).toBeUndefined()
    expect(validateNotas(`  ${'x'.repeat(500)}  `)).toBeUndefined()
    expect(validateNotas('x'.repeat(501))).toBe(CHECKOUT_VALIDATION_MESSAGES.NOTAS_MAX_LENGTH)
  })
})

describe('CarritoPage (/carrito)', () => {
  it('muestra EstadoVacio y navega al catálogo cuando no hay productos', async () => {
    const user = userEvent.setup()

    renderWithProviders(
      <>
        <LocationProbe />
        <Routes>
          <Route path="/carrito" element={<CarritoPage />} />
          <Route path="/" element={<div>Catálogo principal</div>} />
        </Routes>
      </>,
      ['/carrito'],
    )

    expect(screen.getByRole('heading', { name: 'Carrito de compras' })).toBeInTheDocument()
    expect(screen.getByText('El carrito está vacío')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Ir al catálogo' }))

    expect(screen.getByTestId('current-path')).toHaveTextContent('/')
  })

  it('permite ajustar cantidades, quitar ítems, vaciar carrito y continuar al checkout', async () => {
    const user = userEvent.setup()
    seedCart()

    renderWithProviders(
      <>
        <LocationProbe />
        <Routes>
          <Route path="/carrito" element={<CarritoPage />} />
          <Route path="/checkout" element={<div>Pantalla checkout</div>} />
        </Routes>
      </>,
      ['/carrito'],
    )

    expect(screen.getByText('Hamburguesa Clásica')).toBeInTheDocument()
    expect(screen.getByText('Gaseosa Cola 500ml')).toBeInTheDocument()
    expect(screen.getByText(/\$\s*6\.500,00/)).toBeInTheDocument()
    expect(screen.getByText(/\$\s*13\.000,00/)).toBeInTheDocument()
    expect(screen.getByText(/\$\s*14\.800,00/)).toBeInTheDocument()

    await user.click(
      screen.getByRole('button', { name: 'Aumentar cantidad de Hamburguesa Clásica' }),
    )
    expect(useCartStore.getState().items[0].cantidad).toBe(3)
    expect(screen.getByText(/\$\s*21\.300,00/)).toBeInTheDocument()

    await user.click(
      screen.getByRole('button', { name: 'Disminuir cantidad de Hamburguesa Clásica' }),
    )
    expect(useCartStore.getState().items[0].cantidad).toBe(2)

    const qtyInput = screen.getByRole('spinbutton', { name: 'Cantidad de Hamburguesa Clásica' })
    fireEvent.change(qtyInput, { target: { value: '4' } })
    expect(useCartStore.getState().items[0].cantidad).toBe(4)

    await user.click(
      screen.getByRole('button', { name: 'Quitar Gaseosa Cola 500ml del carrito' }),
    )
    expect(screen.queryByText('Gaseosa Cola 500ml')).not.toBeInTheDocument()
    expect(useCartStore.getState().items).toHaveLength(1)

    await user.click(screen.getByRole('button', { name: 'Continuar al checkout' }))
    expect(screen.getByTestId('current-path')).toHaveTextContent('/checkout')

    // Verifica acción de vaciado sobre un carrito poblado.
    useCartStore.setState({ items: [{ producto_id: 2, nombre: 'Pizza', precio_unitario: 8000, cantidad: 1 }] })
    renderWithProviders(<CarritoPage />, ['/carrito'])
    await user.click(screen.getByRole('button', { name: 'Vaciar carrito' }))
    expect(useCartStore.getState().items).toHaveLength(0)
  })
})

describe('CheckoutPage (/checkout)', () => {
  it('redirige a /login si el usuario no está autenticado', async () => {
    seedCart()

    renderWithProviders(
      <>
        <LocationProbe />
        <AppRoutes />
      </>,
      ['/checkout'],
    )

    await waitFor(() => {
      expect(screen.getByTestId('current-path')).toHaveTextContent('/login')
    })
  })

  it('bloquea el checkout mostrando EstadoVacio si el carrito está vacío', async () => {
    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })
    const postSpy = vi.fn()
    axiosInstance.defaults.adapter = (async (config) => {
      postSpy(config.url)
      return createAxiosResponse(config, 201, {})
    }) satisfies AxiosAdapter

    renderWithProviders(<CheckoutPage />, ['/checkout'])

    expect(screen.getByText('Tu carrito está vacío')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirmar pedido' })).not.toBeInTheDocument()
    expect(postSpy).not.toHaveBeenCalled()
  })

  it('valida espacios puros y longitudes con aria-invalid, aria-describedby y role="alert"', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })
    seedCart()

    const postSpy = vi.fn()
    axiosInstance.defaults.adapter = (async (config) => {
      postSpy(config.url)
      return createAxiosResponse(config, 201, {})
    }) satisfies AxiosAdapter

    renderWithProviders(<CheckoutPage />, ['/checkout'])

    const direccionInput = screen.getByLabelText('Dirección de entrega')
    const notasInput = screen.getByLabelText('Notas adicionales (opcional)')

    await user.type(direccionInput, '     ')
    await user.type(notasInput, 'n'.repeat(501))
    await user.click(screen.getByRole('button', { name: 'Confirmar pedido' }))

    await waitFor(() => {
      expect(direccionInput).toHaveAttribute('aria-invalid', 'true')
      expect(notasInput).toHaveAttribute('aria-invalid', 'true')
    })

    const alerts = screen.getAllByRole('alert')
    expect(
      alerts.some((node) => node.textContent === CHECKOUT_VALIDATION_MESSAGES.DIRECCION_REQUIRED),
    ).toBe(true)
    expect(
      alerts.some((node) => node.textContent === CHECKOUT_VALIDATION_MESSAGES.NOTAS_MAX_LENGTH),
    ).toBe(true)

    const direccionErrorId = direccionInput.getAttribute('aria-describedby')
    expect(direccionErrorId).toBeTruthy()
    expect(document.getElementById(direccionErrorId!)).toHaveTextContent(
      CHECKOUT_VALIDATION_MESSAGES.DIRECCION_REQUIRED,
    )
    expect(postSpy).not.toHaveBeenCalled()
  })

  it('conserva carrito, formulario y ruta ante error HTTP 400 del backend', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })
    seedCart()

    axiosInstance.defaults.adapter = (async (config) => {
      throw createAxiosHttpError(config, 400, {
        detail: "Stock insuficiente para 'Hamburguesa Clásica'",
      })
    }) satisfies AxiosAdapter

    renderWithProviders(
      <>
        <LocationProbe />
        <Routes>
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/mis-pedidos" element={<div>Mis pedidos</div>} />
        </Routes>
      </>,
      ['/checkout'],
    )

    const direccionInput = screen.getByLabelText('Dirección de entrega')
    const pagoSelect = screen.getByLabelText('Forma de pago')
    const notasInput = screen.getByLabelText('Notas adicionales (opcional)')

    await user.type(direccionInput, 'Av. Corrientes 1234')
    await user.selectOptions(pagoSelect, 'TRANSFERENCIA')
    await user.type(notasInput, 'Sin cebolla')
    await user.click(screen.getByRole('button', { name: 'Confirmar pedido' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        "Stock insuficiente para 'Hamburguesa Clásica'",
      )
    })

    expect(screen.getByTestId('current-path')).toHaveTextContent('/checkout')
    expect(useCartStore.getState().items).toHaveLength(2)
    expect(direccionInput).toHaveValue('Av. Corrientes 1234')
    expect(pagoSelect).toHaveValue('TRANSFERENCIA')
    expect(notasInput).toHaveValue('Sin cebolla')
  })

  it('envía POST /pedidos normalizado, vacía el carrito, invalida queries y redirige a /mis-pedidos tras 201', async () => {
    const user = userEvent.setup()
    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })
    seedCart()

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    let capturedPayload: PedidoCreate | null = null

    const pedidoCreado: PedidoRead = {
      id: 42,
      usuario_id: USER_CLIENTE.id,
      estado: 'PENDIENTE',
      forma_pago: 'TRANSFERENCIA',
      direccion_entrega: 'Av. Siempre Viva 742',
      notas: null,
      total: 14800,
      created_at: '2026-11-21T14:40:00Z',
      updated_at: '2026-11-21T14:40:00Z',
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
    }

    axiosInstance.defaults.adapter = (async (config) => {
      if (config.url === '/pedidos' && config.method?.toLowerCase() === 'post') {
        capturedPayload = JSON.parse(String(config.data)) as PedidoCreate
        return createAxiosResponse(config, 201, pedidoCreado)
      }
      throw createAxiosHttpError(config, 404, { detail: 'No encontrado' })
    }) satisfies AxiosAdapter

    renderWithProviders(
      <>
        <LocationProbe />
        <Routes>
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/mis-pedidos" element={<div>Mis pedidos</div>} />
        </Routes>
      </>,
      ['/checkout'],
    )

    await user.type(screen.getByLabelText('Dirección de entrega'), '  Av. Siempre Viva 742  ')
    await user.selectOptions(screen.getByLabelText('Forma de pago'), 'TRANSFERENCIA')
    await user.type(screen.getByLabelText('Notas adicionales (opcional)'), '   ')
    await user.click(screen.getByRole('button', { name: 'Confirmar pedido' }))

    await waitFor(() => {
      expect(screen.getByTestId('current-path')).toHaveTextContent('/mis-pedidos')
    })

    expect(capturedPayload).toEqual({
      items: [
        { producto_id: 1, cantidad: 2 },
        { producto_id: 3, cantidad: 1 },
      ],
      direccion_entrega: 'Av. Siempre Viva 742',
      forma_pago: 'TRANSFERENCIA',
      notas: null,
    })

    expect(useCartStore.getState().items).toEqual([])
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['pedidos'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['pedidos', 'resumen'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['productos'] })
  })
})
