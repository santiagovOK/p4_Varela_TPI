/**
 * Suite de pruebas unitarias y de integración para el ABM de Categorías y Productos (`E9.2`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Historia `HU-TPI-04`, rutas `/admin/categorias` y `/admin/productos` (págs. 12–14, 18–20).
 */
import { QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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

import type { UserPublic } from '@/features/auth'
import {
  AdminCategoriasPage,
  CATEGORIA_VALIDATION_MESSAGES,
  type CategoriaRead,
  validateCategoriaDescripcion,
  validateCategoriaNombre,
} from '@/features/categorias'
import {
  AdminProductosPage,
  PRODUCTO_VALIDATION_MESSAGES,
  type ProductoRead,
  validateCategoriaId,
  validateImagenUrl,
  validatePrecioBase,
  validateProductoNombre,
  validateStock,
} from '@/features/productos'
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

const CATEGORIAS_FIXTURE: CategoriaRead[] = [
  { id: 1, nombre: 'Hamburguesas', descripcion: 'Clásicas y especiales', activo: true },
  { id: 2, nombre: 'Bebidas', descripcion: 'Gaseosas y aguas', activo: true },
]

function buildProducto(id: number, overrides: Partial<ProductoRead> = {}): ProductoRead {
  const cat = overrides.categoria ?? (id % 2 === 0 ? CATEGORIAS_FIXTURE[1] : CATEGORIAS_FIXTURE[0])
  return {
    id,
    nombre: `Producto ${String(id).padStart(2, '0')}`,
    descripcion: `Descripción ${id}`,
    precio_base: 1500 + id * 100,
    imagen_url: id === 1 ? 'https://cdn.example.com/burger.jpg' : '/img/item.png',
    stock: 10 + id,
    disponible: id % 3 !== 0,
    categoria_id: cat.id,
    activo: true,
    categoria: cat,
    ...overrides,
  }
}

const PRODUCTOS_FIXTURE: ProductoRead[] = Array.from({ length: 12 }, (_, idx) =>
  buildProducto(idx + 1),
)

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

function renderWithProviders(ui: ReactNode, initialEntries: string[] = ['/admin/categorias']) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  localStorage.clear()
  queryClient.clear()
  useAuthStore.setState({
    usuario: USER_ADMIN,
    cargando: false,
    error: null,
  })
  registerAuthInterceptorHandlers()
})

afterEach(() => {
  axiosInstance.defaults.adapter = originalAdapter
  vi.restoreAllMocks()
  queryClient.clear()
})

describe('Validadores puros de Categorías y Productos', () => {
  it('validateCategoriaNombre y validateCategoriaDescripcion aplican .trim() y longitudes', () => {
    expect(validateCategoriaNombre('   ')).toBe(CATEGORIA_VALIDATION_MESSAGES.NOMBRE_REQUIRED)
    expect(validateCategoriaNombre(' A ')).toBe(CATEGORIA_VALIDATION_MESSAGES.NOMBRE_LENGTH)
    expect(validateCategoriaNombre('X'.repeat(101))).toBe(
      CATEGORIA_VALIDATION_MESSAGES.NOMBRE_LENGTH,
    )
    expect(validateCategoriaNombre('  Pizzas  ')).toBeUndefined()

    expect(validateCategoriaDescripcion(null)).toBeUndefined()
    expect(validateCategoriaDescripcion('   ')).toBeUndefined()
    expect(validateCategoriaDescripcion('A'.repeat(501))).toBe(
      CATEGORIA_VALIDATION_MESSAGES.DESCRIPCION_MAX_LENGTH,
    )
  })

  it('validadores de producto verifican nombre, precio_base, stock, categoria_id e imagen_url segura', () => {
    expect(validateProductoNombre('   ')).toBe(PRODUCTO_VALIDATION_MESSAGES.NOMBRE_REQUIRED)
    expect(validateProductoNombre('  Empanada  ')).toBeUndefined()

    expect(validatePrecioBase(-1)).toBe(PRODUCTO_VALIDATION_MESSAGES.PRECIO_BASE_INVALID)
    expect(validatePrecioBase('')).toBe(PRODUCTO_VALIDATION_MESSAGES.PRECIO_BASE_INVALID)
    expect(validatePrecioBase('0')).toBeUndefined()
    expect(validatePrecioBase(2500.5)).toBeUndefined()

    expect(validateStock(-1)).toBe(PRODUCTO_VALIDATION_MESSAGES.STOCK_INVALID)
    expect(validateStock('1.5')).toBe(PRODUCTO_VALIDATION_MESSAGES.STOCK_INVALID)
    expect(validateStock('0')).toBeUndefined()
    expect(validateStock(25)).toBeUndefined()

    expect(validateCategoriaId('')).toBe(PRODUCTO_VALIDATION_MESSAGES.CATEGORIA_REQUIRED)
    expect(validateCategoriaId(0)).toBe(PRODUCTO_VALIDATION_MESSAGES.CATEGORIA_REQUIRED)
    expect(validateCategoriaId('2')).toBeUndefined()

    expect(validateImagenUrl(null)).toBeUndefined()
    expect(validateImagenUrl('   ')).toBeUndefined()
    expect(validateImagenUrl('https://cdn.example.com/foto.png')).toBeUndefined()
    expect(validateImagenUrl('http://localhost:8000/img/a.jpg')).toBeUndefined()
    expect(validateImagenUrl('/img/burger.png')).toBeUndefined()
    expect(validateImagenUrl('javascript:alert(1)')).toBe(
      PRODUCTO_VALIDATION_MESSAGES.IMAGEN_URL_INVALID,
    )
    expect(validateImagenUrl('data:image/png;base64,abc')).toBe(
      PRODUCTO_VALIDATION_MESSAGES.IMAGEN_URL_INVALID,
    )
    expect(validateImagenUrl('vbscript:msgbox(1)')).toBe(
      PRODUCTO_VALIDATION_MESSAGES.IMAGEN_URL_INVALID,
    )
    expect(validateImagenUrl('//evil.example.com/x.png')).toBe(
      PRODUCTO_VALIDATION_MESSAGES.IMAGEN_URL_INVALID,
    )
    expect(validateImagenUrl('/img/../secret.png')).toBe(
      PRODUCTO_VALIDATION_MESSAGES.IMAGEN_URL_INVALID,
    )
  })
})

describe('AdminCategoriasPage (/admin/categorias)', () => {
  it('renderiza tabla semántica, ordena por Nombre y filtra localmente', async () => {
    const user = userEvent.setup()
    axiosInstance.defaults.adapter = (async (config) => {
      if (config.url === '/categorias' && config.method === 'get') {
        return createAxiosResponse(config, 200, CATEGORIAS_FIXTURE)
      }
      throw new Error(`Unexpected request: ${config.method} ${config.url}`)
    }) as AxiosAdapter

    renderWithProviders(<AdminCategoriasPage />)

    expect(await screen.findByText('Hamburguesas')).toBeInTheDocument()
    expect(screen.getByText('Bebidas')).toBeInTheDocument()

    const nombreHeader = screen.getByRole('columnheader', { name: /Nombre/i })
    expect(nombreHeader).toHaveAttribute('aria-sort', 'none')

    await user.click(within(nombreHeader).getByRole('button'))
    expect(nombreHeader).toHaveAttribute('aria-sort', 'ascending')

    const rows = screen.getAllByRole('row')
    expect(within(rows[1]).getByText('Bebidas')).toBeInTheDocument()
    expect(within(rows[2]).getByText('Hamburguesas')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Buscar categoría'), 'Hamb')
    expect(screen.getByText('Hamburguesas')).toBeInTheDocument()
    expect(screen.queryByText('Bebidas')).not.toBeInTheDocument()
  })

  it('crea categoría con validación en cliente e invalidación cruzada de categorias y productos', async () => {
    const user = userEvent.setup()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    let categorias = [...CATEGORIAS_FIXTURE]

    axiosInstance.defaults.adapter = (async (config) => {
      if (config.url === '/categorias' && config.method === 'get') {
        return createAxiosResponse(config, 200, categorias)
      }
      if (config.url === '/categorias' && config.method === 'post') {
        const body = JSON.parse(String(config.data)) as {
          nombre: string
          descripcion: string | null
        }
        const created: CategoriaRead = {
          id: 3,
          nombre: body.nombre,
          descripcion: body.descripcion,
          activo: true,
        }
        categorias = [...categorias, created]
        return createAxiosResponse(config, 201, created)
      }
      throw new Error(`Unexpected request: ${config.method} ${config.url}`)
    }) as AxiosAdapter

    renderWithProviders(<AdminCategoriasPage />)
    await screen.findByText('Hamburguesas')

    await user.click(screen.getByRole('button', { name: 'Nueva categoría' }))
    const dialog = screen.getByRole('dialog')

    // Envío vacío dispara validación pura
    await user.click(within(dialog).getByRole('button', { name: 'Crear categoría' }))
    expect(
      await within(dialog).findByText(CATEGORIA_VALIDATION_MESSAGES.NOMBRE_REQUIRED),
    ).toBeInTheDocument()
    const nombreInput = within(dialog).getByLabelText('Nombre')
    expect(nombreInput).toHaveAttribute('aria-invalid', 'true')
    expect(nombreInput).toHaveAttribute('aria-describedby')

    await user.type(nombreInput, '  Postres  ')
    await user.type(within(dialog).getByLabelText('Descripción (opcional)'), '  Tortas y helados  ')
    await user.click(within(dialog).getByRole('button', { name: 'Crear categoría' }))

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
    expect(await screen.findByText('Postres')).toBeInTheDocument()
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['categorias'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['productos'] })
  })

  it('preserva modal abierto y valores ante 409 Conflict y bloquea Escape/backdrop mientras isPending', async () => {
    const user = userEvent.setup()
    let resolvePending!: (res: AxiosResponse) => void
    let callCount = 0

    axiosInstance.defaults.adapter = (async (config) => {
      if (config.url === '/categorias' && config.method === 'get') {
        return createAxiosResponse(config, 200, CATEGORIAS_FIXTURE)
      }
      if (config.url === '/categorias/1' && config.method === 'put') {
        callCount += 1
        if (callCount === 1) {
          return await new Promise<AxiosResponse>((resolve) => {
            resolvePending = resolve
          })
        }
        throw createAxiosHttpError(config, 409, {
          detail: 'Ya existe una categoría con ese nombre',
        })
      }
      throw new Error(`Unexpected request: ${config.method} ${config.url}`)
    }) as AxiosAdapter

    renderWithProviders(<AdminCategoriasPage />)
    await screen.findByText('Hamburguesas')

    const editButtons = screen.getAllByRole('button', { name: 'Editar' })
    await user.click(editButtons[0])

    const dialog = screen.getByRole('dialog')
    const nombreInput = within(dialog).getByLabelText('Nombre')
    await user.clear(nombreInput)
    await user.type(nombreInput, 'Bebidas')
    await user.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }))

    await waitFor(() => {
      expect(dialog).toHaveAttribute('aria-busy', 'true')
    })

    // Escape y clic en backdrop no cierran el modal mientras isPending
    fireEvent.keyDown(document, { key: 'Escape' })
    await user.click(screen.getByTestId('modal-backdrop'))
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    resolvePending(createAxiosResponse({} as InternalAxiosRequestConfig, 200, CATEGORIAS_FIXTURE[0]))
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    // Segundo intento con error 409 conserva modal abierto y texto editado
    await user.click(screen.getAllByRole('button', { name: 'Editar' })[0])
    const dialog2 = screen.getByRole('dialog')
    const nombreInput2 = within(dialog2).getByLabelText('Nombre')
    await user.clear(nombreInput2)
    await user.type(nombreInput2, 'Bebidas')
    await user.click(within(dialog2).getByRole('button', { name: 'Guardar cambios' }))

    const alert = await within(dialog2).findByRole('alert')
    expect(alert).toHaveTextContent('Ya existe una categoría con ese nombre')
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(within(dialog2).getByLabelText('Nombre')).toHaveValue('Bebidas')
  })

  it('elimina categoría (204), ejecuta removeQueries(["categorias", id]) y conserva datos ante refetch fallido', async () => {
    const user = userEvent.setup()
    const removeSpy = vi.spyOn(queryClient, 'removeQueries')
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    let getCount = 0

    axiosInstance.defaults.adapter = (async (config) => {
      if (config.url === '/categorias' && config.method === 'get') {
        getCount += 1
        if (getCount === 1) {
          return createAxiosResponse(config, 200, CATEGORIAS_FIXTURE)
        }
        throw createAxiosHttpError(config, 500, { detail: 'Error temporal de red' })
      }
      if (config.url === '/categorias/1' && config.method === 'delete') {
        return createAxiosResponse(config, 204, null)
      }
      throw new Error(`Unexpected request: ${config.method} ${config.url}`)
    }) as AxiosAdapter

    renderWithProviders(<AdminCategoriasPage />)
    await screen.findByText('Hamburguesas')

    await user.click(screen.getAllByRole('button', { name: 'Eliminar' })[0])
    const dialog = screen.getByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Confirmar eliminación' }))

    await waitFor(() => {
      expect(removeSpy).toHaveBeenCalledWith({ queryKey: ['categorias', 1] })
    })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['categorias'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['productos'] })

    // Refetch posterior fallido conserva la tabla anterior y muestra aviso inline-refetch
    expect(
      await screen.findByText(/No se pudieron actualizar las categorías; se conservan los últimos datos confirmados/i),
    ).toBeInTheDocument()
    expect(screen.getByText('Hamburguesas')).toBeInTheDocument()
  })
})

describe('AdminProductosPage (/admin/productos)', () => {
  it('lista productos con paginación local, filtra por búsqueda/categoría y resetea a pageIndex 0', async () => {
    const user = userEvent.setup()

    axiosInstance.defaults.adapter = (async (config) => {
      if (config.url === '/productos' && config.method === 'get') {
        expect(config.params).toEqual({ skip: 0, limit: 100 })
        return createAxiosResponse(config, 200, {
          total: PRODUCTOS_FIXTURE.length,
          items: PRODUCTOS_FIXTURE,
        })
      }
      if (config.url === '/categorias' && config.method === 'get') {
        return createAxiosResponse(config, 200, CATEGORIAS_FIXTURE)
      }
      throw new Error(`Unexpected request: ${config.method} ${config.url}`)
    }) as AxiosAdapter

    renderWithProviders(<AdminProductosPage />, ['/admin/productos'])

    expect(await screen.findByText('Producto 01')).toBeInTheDocument()
    expect(screen.getByText(/Página 1 de 2/i)).toBeInTheDocument()
    expect(screen.queryByText('Producto 11')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(screen.getByText(/Página 2 de 2/i)).toBeInTheDocument()
    expect(screen.getByText('Producto 11')).toBeInTheDocument()

    // Filtrar por categoría debe resetear automáticamente a Página 1
    await user.selectOptions(screen.getByLabelText('Filtrar por categoría'), '1')
    expect(screen.getByText(/Página 1 de 1/i)).toBeInTheDocument()
    expect(screen.getByText('Producto 01')).toBeInTheDocument()
    expect(screen.queryByText('Producto 02')).not.toBeInTheDocument()

    // Filtrar por búsqueda
    await user.type(screen.getByLabelText('Buscar producto'), 'Producto 05')
    expect(screen.getByText('Producto 05')).toBeInTheDocument()
    expect(screen.queryByText('Producto 01')).not.toBeInTheDocument()
  })

  it('crea producto, actualiza stock (PATCH /stock), preserva modal ante error 400 y elimina con removeQueries', async () => {
    const user = userEvent.setup()
    const removeSpy = vi.spyOn(queryClient, 'removeQueries')
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    let productos = [PRODUCTOS_FIXTURE[0], PRODUCTOS_FIXTURE[1]]
    let failCreate = true

    axiosInstance.defaults.adapter = (async (config) => {
      if (config.url === '/productos' && config.method === 'get') {
        return createAxiosResponse(config, 200, {
          total: productos.length,
          items: productos,
        })
      }
      if (config.url === '/categorias' && config.method === 'get') {
        return createAxiosResponse(config, 200, CATEGORIAS_FIXTURE)
      }
      if (config.url === '/productos' && config.method === 'post') {
        if (failCreate) {
          failCreate = false
          throw createAxiosHttpError(config, 400, { detail: 'Datos de producto inválidos' })
        }
        const body = JSON.parse(String(config.data)) as {
          nombre: string
          precio_base: number
          stock: number
          disponible: boolean
          categoria_id: number
          imagen_url: string | null
        }
        const created = buildProducto(99, {
          nombre: body.nombre,
          precio_base: body.precio_base,
          stock: body.stock,
          disponible: body.disponible,
          categoria_id: body.categoria_id,
          imagen_url: body.imagen_url,
          categoria: CATEGORIAS_FIXTURE[0],
        })
        productos = [...productos, created]
        return createAxiosResponse(config, 201, created)
      }
      if (config.url === '/productos/1/stock' && config.method === 'patch') {
        const body = JSON.parse(String(config.data)) as { stock: number; disponible: boolean }
        const updated = { ...productos[0], stock: body.stock, disponible: body.disponible }
        productos = [updated, productos[1]]
        return createAxiosResponse(config, 200, updated)
      }
      if (config.url === '/productos/2' && config.method === 'delete') {
        productos = [productos[0]]
        return createAxiosResponse(config, 204, null)
      }
      throw new Error(`Unexpected request: ${config.method} ${config.url}`)
    }) as AxiosAdapter

    renderWithProviders(<AdminProductosPage />, ['/admin/productos'])
    await screen.findByText('Producto 01')

    // Alta con error 400 -> preserva modal y datos, luego éxito
    await user.click(screen.getByRole('button', { name: 'Nuevo producto' }))
    const createDialog = screen.getByRole('dialog')
    await user.type(within(createDialog).getByLabelText('Nombre'), 'Lomito completo')
    await user.type(within(createDialog).getByLabelText('Precio base'), '4500')
    await user.selectOptions(within(createDialog).getByLabelText('Categoría'), '1')
    await user.type(within(createDialog).getByLabelText('URL de imagen (opcional)'), '/img/lomito.png')
    await user.click(within(createDialog).getByRole('button', { name: 'Crear producto' }))

    expect(await within(createDialog).findByText('Datos de producto inválidos')).toBeInTheDocument()
    expect(within(createDialog).getByLabelText('Nombre')).toHaveValue('Lomito completo')

    await user.click(within(createDialog).getByRole('button', { name: 'Crear producto' }))
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
    expect(await screen.findByText('Lomito completo')).toBeInTheDocument()

    // Actualización de stock PATCH /productos/1/stock (el índice 0 es el encabezado ordenable)
    const firstDataRow = screen.getAllByRole('row')[1]
    await user.click(within(firstDataRow).getByRole('button', { name: 'Stock' }))
    const stockDialog = screen.getByRole('dialog')
    const stockInput = within(stockDialog).getByLabelText('Stock disponible')
    await user.clear(stockInput)
    await user.type(stockInput, '25')
    await user.click(within(stockDialog).getByRole('button', { name: 'Guardar stock' }))

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
    expect(await screen.findByText('25')).toBeInTheDocument()

    // Baja lógica DELETE /productos/2
    await user.click(screen.getAllByRole('button', { name: 'Eliminar' })[1])
    const deleteDialog = screen.getByRole('dialog')
    await user.click(within(deleteDialog).getByRole('button', { name: 'Confirmar eliminación' }))

    await waitFor(() => {
      expect(removeSpy).toHaveBeenCalledWith({ queryKey: ['productos', 2] })
    })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['productos'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['categorias'] })
  })

  it('integra /admin/categorias y /admin/productos en AppRoutes para rol admin', async () => {
    axiosInstance.defaults.adapter = (async (config) => {
      if (config.url === '/categorias' && config.method === 'get') {
        return createAxiosResponse(config, 200, CATEGORIAS_FIXTURE)
      }
      if (config.url === '/productos' && config.method === 'get') {
        return createAxiosResponse(config, 200, { total: 1, items: [PRODUCTOS_FIXTURE[0]] })
      }
      throw new Error(`Unexpected request: ${config.method} ${config.url}`)
    }) as AxiosAdapter

    const { unmount } = renderWithProviders(<AppRoutes />, ['/admin/categorias'])
    expect(await screen.findByRole('heading', { name: 'Administración de categorías' })).toBeInTheDocument()
    unmount()

    renderWithProviders(<AppRoutes />, ['/admin/productos'])
    expect(await screen.findByRole('heading', { name: 'Administración de productos' })).toBeInTheDocument()
  })
})
