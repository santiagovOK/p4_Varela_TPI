/**
 * Pruebas unitarias y de integración para el catálogo público (`CatalogoPage` y `ProductoCard`, `E8.2`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - HU-TPI-02 (págs. 12–14, 18–20): listado paginado, búsqueda, filtro, imágenes seguras y carrito.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  AxiosError,
  type AxiosAdapter,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { CategoriaRead } from '@/features/categorias'
import {
  CatalogoPage,
  ProductoCard,
  isValidImageUrl,
  type ProductoRead,
} from '@/features/productos'
import { AppRoutes } from '@/routes/AppRouter'
import { axiosInstance } from '@/shared/api/axiosInstance'
import { registerAuthInterceptorHandlers, useAuthStore } from '@/store/authStore'
import { useCartStore } from '@/store/cartStore'

const originalAdapter = axiosInstance.defaults.adapter

const CATEGORIAS_MOCK: CategoriaRead[] = [
  { id: 1, nombre: 'Hamburguesas', descripcion: 'A la parrilla', activo: true },
  { id: 2, nombre: 'Pizzas', descripcion: 'A la piedra', activo: true },
]

const PRODUCTOS_MOCK: ProductoRead[] = [
  {
    id: 10,
    nombre: 'Hamburguesa Clásica',
    descripcion: 'Medallón vacuno con queso cheddar',
    precio_base: 8500,
    imagen_url: '/img/hamburguesa-clasica.jpg',
    stock: 12,
    disponible: true,
    categoria_id: 1,
    activo: true,
    categoria: CATEGORIAS_MOCK[0],
  },
  {
    id: 11,
    nombre: 'Pizza Muzzarella',
    descripcion: 'Salsa casera y muzzarella',
    precio_base: 9200,
    imagen_url: 'https://cdn.example.com/pizza.jpg',
    stock: 0,
    disponible: true,
    categoria_id: 2,
    activo: true,
    categoria: CATEGORIAS_MOCK[1],
  },
  {
    id: 12,
    nombre: 'Pizza Napolitana',
    descripcion: 'Tomate fresco y albahaca',
    precio_base: 10200,
    imagen_url: '/img/pizza-napolitana.jpg',
    stock: 5,
    disponible: false,
    categoria_id: 2,
    activo: true,
    categoria: CATEGORIAS_MOCK[1],
  },
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
    AxiosError.ERR_BAD_RESPONSE,
    config,
    undefined,
    response,
  )
}

function renderWithProviders(ui: ReactNode, initialEntries: string[] = ['/']) {
  const testQueryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return {
    testQueryClient,
    ...render(
      <QueryClientProvider client={testQueryClient}>
        <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>
      </QueryClientProvider>,
    ),
  }
}

beforeEach(() => {
  localStorage.clear()
  registerAuthInterceptorHandlers()
  useAuthStore.setState({ usuario: null, cargando: false, error: null })
  useCartStore.setState({ items: [] })
})

afterEach(() => {
  axiosInstance.defaults.adapter = originalAdapter
  localStorage.clear()
  vi.restoreAllMocks()
})

describe('isValidImageUrl y ProductoCard (seguridad y fallback)', () => {
  it('acepta https://, http:// y /img/ y rechaza esquemas peligrosos o inválidos', () => {
    expect(isValidImageUrl('https://cdn.example.com/a.jpg')).toBe(true)
    expect(isValidImageUrl('http://localhost:8000/img/a.jpg')).toBe(true)
    expect(isValidImageUrl('/img/hamburguesa-clasica.jpg')).toBe(true)

    expect(isValidImageUrl(null)).toBe(false)
    expect(isValidImageUrl(undefined)).toBe(false)
    expect(isValidImageUrl('')).toBe(false)
    expect(isValidImageUrl('   ')).toBe(false)
    expect(isValidImageUrl('javascript:alert(1)')).toBe(false)
    expect(isValidImageUrl('data:image/png;base64,AAA')).toBe(false)
    expect(isValidImageUrl('vbscript:msgbox(1)')).toBe(false)
    expect(isValidImageUrl('//evil.example.com/a.jpg')).toBe(false)
    expect(isValidImageUrl('/img/../secret.jpg')).toBe(false)
  })

  it('renderiza imagen con alt y cambia a fallback aria-hidden sin reintentar ante onError', () => {
    render(<ProductoCard producto={PRODUCTOS_MOCK[0]} />)

    const img = screen.getByRole('img', { name: 'Hamburguesa Clásica' })
    expect(img).toHaveAttribute('src', '/img/hamburguesa-clasica.jpg')

    fireEvent.error(img)

    expect(screen.queryByRole('img', { name: 'Hamburguesa Clásica' })).not.toBeInTheDocument()
    expect(screen.getByText('Imagen no disponible')).toBeInTheDocument()
    const fallbackContainer = screen.getByText('Imagen no disponible').parentElement
    expect(fallbackContainer?.querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
  })

  it('renderiza directamente el fallback cuando imagen_url es null o esquema bloqueado', () => {
    const productoNull: ProductoRead = { ...PRODUCTOS_MOCK[0], imagen_url: null }
    const { rerender } = render(<ProductoCard producto={productoNull} />)
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(screen.getByText('Imagen no disponible')).toBeInTheDocument()

    const productoXss: ProductoRead = {
      ...PRODUCTOS_MOCK[0],
      imagen_url: 'javascript:alert(1)',
    }
    rerender(<ProductoCard producto={productoXss} />)
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(screen.getByText('Imagen no disponible')).toBeInTheDocument()
  })
})

describe('CatalogoPage (listado, filtros, paginación, carrito y estados)', () => {
  it('muestra Skeleton en carga inicial y luego renderiza los productos solicitando disponible=true', async () => {
    let resolveProductos!: (res: AxiosResponse) => void
    const productosPending = new Promise<AxiosResponse>((resolve) => {
      resolveProductos = resolve
    })

    const adapterSpy = vi.fn<AxiosAdapter>(async (config) => {
      if (config.url === '/categorias') {
        return createAxiosResponse(config, 200, CATEGORIAS_MOCK)
      }
      if (config.url === '/productos') {
        return productosPending.then((res) => ({ ...res, config }))
      }
      return createAxiosResponse(config, 404, { detail: 'Not found' })
    })
    axiosInstance.defaults.adapter = adapterSpy

    renderWithProviders(<CatalogoPage />)

    const skeleton = screen.getByRole('status')
    expect(skeleton).toHaveAttribute('aria-busy', 'true')

    resolveProductos(
      createAxiosResponse({} as InternalAxiosRequestConfig, 200, {
        total: 1,
        items: [PRODUCTOS_MOCK[0]],
      }),
    )

    expect(
      await screen.findByRole('heading', { name: 'Hamburguesa Clásica' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Stock: 12')).toBeInTheDocument()

    const productosCall = adapterSpy.mock.calls.find(
      ([cfg]) => cfg.url === '/productos',
    )?.[0]
    expect(productosCall?.params).toEqual({
      skip: 0,
      limit: 8,
      disponible: true,
    })
  })

  it('aplica .trim() en búsqueda, filtra por categoría y resetea skip a 0 desde página 2', async () => {
    const user = userEvent.setup()
    const requests: Array<Record<string, unknown>> = []

    const adapterSpy = vi.fn<AxiosAdapter>(async (config) => {
      if (config.url === '/categorias') {
        return createAxiosResponse(config, 200, CATEGORIAS_MOCK)
      }
      if (config.url === '/productos') {
        requests.push((config.params as Record<string, unknown>) ?? {})
        return createAxiosResponse(config, 200, {
          total: 16,
          items: [PRODUCTOS_MOCK[0]],
        })
      }
      return createAxiosResponse(config, 404, { detail: 'Not found' })
    })
    axiosInstance.defaults.adapter = adapterSpy

    renderWithProviders(<CatalogoPage />)

    await screen.findByRole('heading', { name: 'Hamburguesa Clásica' })

    // Ir a página 2 (skip = 8)
    await user.click(screen.getByRole('button', { name: 'Siguiente' }))
    await waitFor(() => {
      expect(requests.at(-1)).toEqual({ skip: 8, limit: 8, disponible: true })
    })

    // Cambiar categoría resetea skip a 0
    await user.selectOptions(screen.getByLabelText('Categoría'), '2')
    await waitFor(() => {
      expect(requests.at(-1)).toEqual({
        skip: 0,
        limit: 8,
        categoria_id: 2,
        disponible: true,
      })
    })

    // Volver a página 2 y escribir búsqueda con espacios -> .trim() y skip = 0
    await user.click(screen.getByRole('button', { name: 'Siguiente' }))
    await waitFor(() => {
      expect(requests.at(-1)?.skip).toBe(8)
    })

    await user.type(screen.getByLabelText('Buscar productos'), '  pizza  ')
    await waitFor(() => {
      expect(requests.at(-1)).toEqual({
        skip: 0,
        limit: 8,
        search: 'pizza',
        categoria_id: 2,
        disponible: true,
      })
    })
  })

  it('agrega productos disponibles al carrito y bloquea los sin stock o no disponibles', async () => {
    const user = userEvent.setup()
    axiosInstance.defaults.adapter = vi.fn<AxiosAdapter>(async (config) => {
      if (config.url === '/categorias') {
        return createAxiosResponse(config, 200, CATEGORIAS_MOCK)
      }
      if (config.url === '/productos') {
        return createAxiosResponse(config, 200, {
          total: 3,
          items: PRODUCTOS_MOCK,
        })
      }
      return createAxiosResponse(config, 404, { detail: 'Not found' })
    })

    renderWithProviders(<AppRoutes />, ['/'])

    const btnDisponible = await screen.findByRole('button', {
      name: 'Agregar Hamburguesa Clásica al carrito',
    })
    const btnSinStock = screen.getByRole('button', {
      name: 'Agregar Pizza Muzzarella al carrito',
    })
    const btnNoDisponible = screen.getByRole('button', {
      name: 'Agregar Pizza Napolitana al carrito',
    })

    expect(btnDisponible).toBeEnabled()
    expect(btnSinStock).toBeDisabled()
    expect(btnNoDisponible).toBeDisabled()
    expect(screen.getAllByText('Sin stock')).toHaveLength(2)

    await user.click(btnDisponible)

    expect(useCartStore.getState().items).toEqual([
      {
        producto_id: 10,
        nombre: 'Hamburguesa Clásica',
        precio_unitario: 8500,
        cantidad: 1,
      },
    ])
    expect(screen.getByRole('link', { name: /Carrito/i })).toHaveTextContent('1')
  })

  it('muestra EstadoVacio y permite limpiar filtros activos', async () => {
    const user = userEvent.setup()
    axiosInstance.defaults.adapter = vi.fn<AxiosAdapter>(async (config) => {
      if (config.url === '/categorias') {
        return createAxiosResponse(config, 200, CATEGORIAS_MOCK)
      }
      if (config.url === '/productos') {
        const params = (config.params as Record<string, unknown>) ?? {}
        if (params.search === 'inexistente') {
          return createAxiosResponse(config, 200, { total: 0, items: [] })
        }
        return createAxiosResponse(config, 200, {
          total: 1,
          items: [PRODUCTOS_MOCK[0]],
        })
      }
      return createAxiosResponse(config, 404, { detail: 'Not found' })
    })

    renderWithProviders(<CatalogoPage />)

    await screen.findByRole('heading', { name: 'Hamburguesa Clásica' })

    await user.type(screen.getByLabelText('Buscar productos'), 'inexistente')
    expect(await screen.findByText('No se encontraron productos')).toBeInTheDocument()

    const limpiarBtns = screen.getAllByRole('button', { name: 'Limpiar filtros' })
    await user.click(limpiarBtns[0])

    expect(
      await screen.findByRole('heading', { name: 'Hamburguesa Clásica' }),
    ).toBeInTheDocument()
  })

  it('muestra EstadoError alert si falla la carga inicial sin datos previos', async () => {
    axiosInstance.defaults.adapter = vi.fn<AxiosAdapter>(async (config) => {
      if (config.url === '/categorias') {
        return createAxiosResponse(config, 200, CATEGORIAS_MOCK)
      }
      if (config.url === '/productos') {
        throw createAxiosHttpError(config, 500, { detail: 'Error interno del servidor' })
      }
      return createAxiosResponse(config, 404, { detail: 'Not found' })
    })

    renderWithProviders(<CatalogoPage />)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('No se pudo cargar el catálogo')
  })

  it('muestra EstadoError inline-refetch conservando tarjetas previas cuando falla un refetch posterior', async () => {
    const user = userEvent.setup()
    let failNextProductos = false

    axiosInstance.defaults.adapter = vi.fn<AxiosAdapter>(async (config) => {
      if (config.url === '/categorias') {
        return createAxiosResponse(config, 200, CATEGORIAS_MOCK)
      }
      if (config.url === '/productos') {
        if (failNextProductos) {
          throw createAxiosHttpError(config, 500, { detail: 'Fallo temporal de red' })
        }
        return createAxiosResponse(config, 200, {
          total: 16,
          items: [PRODUCTOS_MOCK[0]],
        })
      }
      return createAxiosResponse(config, 404, { detail: 'Not found' })
    })

    renderWithProviders(<CatalogoPage />)

    await screen.findByRole('heading', { name: 'Hamburguesa Clásica' })

    failNextProductos = true
    await user.click(screen.getByRole('button', { name: 'Siguiente' }))

    const refetchStatus = await screen.findByRole('status')
    expect(refetchStatus).toHaveTextContent(
      'No se pudieron actualizar los datos; se conservan los últimos datos confirmados.',
    )
    expect(
      screen.getByRole('heading', { name: 'Hamburguesa Clásica' }),
    ).toBeInTheDocument()
  })
})
