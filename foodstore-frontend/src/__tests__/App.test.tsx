// Consigna: docs/consignas_examen_2.md, 4/R4 y 7/HU-P2-03 — Pruebas de integración de App.tsx, levantamiento de estado y operaciones fetch.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App, { extraerMensajeErrorApi } from '../App'
import type { Producto, UnidadMedida } from '../types'
import { normalizarNumeroInput, obtenerValoresIniciales } from '../components'

const mockUnidades: UnidadMedida[] = [
  {
    id: 1,
    nombre: 'Kilogramo',
    simbolo: 'kg',
    tipo: 'peso',
  },
  {
    id: 2,
    nombre: 'Unidad',
    simbolo: 'u',
    tipo: 'contable',
  },
]

const mockProductos: Producto[] = [
  {
    id: 1,
    nombre: 'Manzanas Red Delicious',
    descripcion: 'Manzanas rojas seleccionadas',
    precio_base: 1500.5,
    unidad_venta_id: 1,
    unidad_venta: mockUnidades[0],
    stock_cantidad: 25.5,
    disponible: true,
    activo: true,
    anulado_at: null,
    hay_stock: true,
    categorias: [],
  },
  {
    id: 2,
    nombre: 'Alfajor Artesanal',
    descripcion: 'Alfajor de dulce de leche',
    precio_base: 800,
    unidad_venta_id: 2,
    unidad_venta: mockUnidades[1],
    stock_cantidad: 0,
    disponible: false,
    activo: true,
    anulado_at: null,
    hay_stock: false,
    categorias: [],
  },
]

describe('extraerMensajeErrorApi', () => {
  it('extrae string simple desde detail', async () => {
    const res = new Response(JSON.stringify({ detail: 'Error de prueba' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    })
    const msg = await extraerMensajeErrorApi(res, 'Fallback')
    expect(msg).toBe('Error de prueba')
  })

  it('extrae array de validaciones de FastAPI unidas por punto y coma', async () => {
    const res = new Response(
      JSON.stringify({
        detail: [
          { loc: ['body', 'nombre'], msg: 'El nombre es obligatorio' },
          { loc: ['body', 'precio_base'], msg: 'El precio debe ser positivo' },
        ],
      }),
      { status: 422, headers: { 'Content-Type': 'application/json' } },
    )
    const msg = await extraerMensajeErrorApi(res, 'Fallback')
    expect(msg).toBe('El nombre es obligatorio; El precio debe ser positivo')
  })

  it('retorna fallback cuando el cuerpo no es JSON o no tiene detail', async () => {
    const res = new Response('Not Found', { status: 404 })
    const msg = await extraerMensajeErrorApi(res, 'Mensaje fallback')
    expect(msg).toBe('Mensaje fallback')
  })
})
describe('normalizarNumeroInput y obtenerValoresIniciales', () => {
  it('elimina ceros decimales redundantes en cadenas y números', () => {
    expect(normalizarNumeroInput('30.000')).toBe('30')
    expect(normalizarNumeroInput('3.500')).toBe('3.5')
    expect(normalizarNumeroInput('1500.00')).toBe('1500')
    expect(normalizarNumeroInput('1250.50')).toBe('1250.5')
    expect(normalizarNumeroInput(30)).toBe('30')
    expect(normalizarNumeroInput(25.5)).toBe('25.5')
    expect(normalizarNumeroInput(0)).toBe('0')
    expect(normalizarNumeroInput('')).toBe('')
  })

  it('normaliza precio_base y stock_cantidad al obtener valores iniciales de edición', () => {
    const productoApi = {
      ...mockProductos[1],
      precio_base: '1500.00' as unknown as number,
      stock_cantidad: '30.000' as unknown as number,
    }
    const valores = obtenerValoresIniciales(productoApi)
    expect(valores.precio_base).toBe('1500')
    expect(valores.stock_cantidad).toBe('30')
  })
})


describe('App Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('muestra estado de carga accesible al montar', () => {
    // Retrasar respuesta de fetch para observar estado de carga
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => {}))

    render(<App />)

    const loadingSection = screen.getByRole('status')
    expect(loadingSection).toHaveAttribute('aria-busy', 'true')
    expect(
      screen.getByText('Cargando catálogo de productos...'),
    ).toBeInTheDocument()
  })

  it('muestra mensaje de alerta accesible y reintento si la API falla al cargar', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Error interno del backend' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    render(<App />)

    await waitFor(() => {
      const alertSection = screen.getByRole('alert')
      expect(alertSection).toBeInTheDocument()
      expect(alertSection).toHaveTextContent('Error interno del backend')
    })

    const btnReintentar = screen.getByRole('button', { name: /reintentar/i })
    expect(btnReintentar).toBeInTheDocument()
  })

  it('carga y renderiza productos y catálogo de unidades exitosamente', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.endsWith('/api/v1/productos')) {
        return new Response(JSON.stringify(mockProductos), { status: 200 })
      }
      if (url.endsWith('/api/v1/unidades-medida')) {
        return new Response(JSON.stringify(mockUnidades), { status: 200 })
      }
      return new Response('Not Found', { status: 404 })
    })

    render(<App />)

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: 'Catálogo de Productos' }),
      ).toBeInTheDocument()
    })

    expect(screen.getByText('2 productos activos')).toBeInTheDocument()
    expect(screen.getByText('Manzanas Red Delicious')).toBeInTheDocument()
    expect(screen.getByText('Alfajor Artesanal')).toBeInTheDocument()
  })

  it('muestra estado de lista vacía cuando no hay productos activos', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.endsWith('/api/v1/productos')) {
        return new Response(JSON.stringify([]), { status: 200 })
      }
      if (url.endsWith('/api/v1/unidades-medida')) {
        return new Response(JSON.stringify(mockUnidades), { status: 200 })
      }
      return new Response('Not Found', { status: 404 })
    })

    render(<App />)

    await waitFor(() => {
      expect(
        screen.getByText('No hay productos registrados en el catálogo'),
      ).toBeInTheDocument()
    })
  })

  it('crea un producto exitosamente mediante POST y actualiza el catálogo', async () => {
    const user = userEvent.setup()
    const nuevoProd: Producto = {
      id: 3,
      nombre: 'Pera Williams',
      descripcion: 'Peras jugosas',
      precio_base: 1200,
      unidad_venta_id: 1,
      unidad_venta: mockUnidades[0],
      stock_cantidad: 10,
      disponible: true,
      activo: true,
      anulado_at: null,
      hay_stock: true,
      categorias: [],
    }
    let productosActuales = [...mockProductos]

    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(async (input, init) => {
        const url = String(input)
        const method = init?.method ?? 'GET'

        if (url.endsWith('/api/v1/productos') && method === 'GET') {
          return new Response(JSON.stringify(productosActuales), {
            status: 200,
          })
        }
        if (url.endsWith('/api/v1/unidades-medida') && method === 'GET') {
          return new Response(JSON.stringify(mockUnidades), { status: 200 })
        }
        if (url.endsWith('/api/v1/productos') && method === 'POST') {
          productosActuales = [...productosActuales, nuevoProd]
          return new Response(JSON.stringify(nuevoProd), { status: 201 })
        }
        return new Response('Not Found', { status: 404 })
      })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Manzanas Red Delicious')).toBeInTheDocument()
    })

    // Abrir modal de nuevo producto
    const btnNuevo = screen.getByRole('button', { name: /nuevo producto/i })
    await user.click(btnNuevo)

    // Modal debe estar abierto
    const modal = screen.getByRole('dialog', { name: /nuevo producto/i })
    expect(modal).toBeInTheDocument()

    // Completar formulario dentro del modal
    await user.type(within(modal).getByLabelText(/nombre/i), 'Pera Williams')
    await user.type(within(modal).getByLabelText(/descripción/i), 'Peras jugosas')
    await user.type(within(modal).getByLabelText(/precio base/i), '1200')
    await user.selectOptions(
      within(modal).getByLabelText(/unidad de venta/i),
      '1', // Kilogramo
    )
    const stockInput = within(modal).getByLabelText(/stock disponible/i)
    await user.clear(stockInput)
    await user.type(stockInput, '10')
    // Enviar formulario
    const btnGuardar = within(modal).getByRole('button', {
      name: /crear producto/i,
    })
    await user.click(btnGuardar)
    // Modal se cierra y el nuevo producto aparece
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      expect(screen.getByText('Pera Williams')).toBeInTheDocument()
    })

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/productos'),
      expect.objectContaining({
        method: 'POST',
      }),
    )
  })

  it('mantiene abierto el modal y muestra role="alert" cuando la API responde HTTP 409 (nombre repetido)', async () => {
    const user = userEvent.setup()

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      const method = init?.method ?? 'GET'

      if (url.endsWith('/api/v1/productos') && method === 'GET') {
        return new Response(JSON.stringify(mockProductos), { status: 200 })
      }
      if (url.endsWith('/api/v1/unidades-medida') && method === 'GET') {
        return new Response(JSON.stringify(mockUnidades), { status: 200 })
      }
      if (url.endsWith('/api/v1/productos') && method === 'POST') {
        return new Response(
          JSON.stringify({
            detail:
              "Ya existe un producto activo con el nombre 'Manzanas Red Delicious'.",
          }),
          { status: 409, headers: { 'Content-Type': 'application/json' } },
        )
      }
      return new Response('Not Found', { status: 404 })
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Manzanas Red Delicious')).toBeInTheDocument()
    })

    // Abrir modal de nuevo producto
    await user.click(screen.getByRole('button', { name: /nuevo producto/i }))
    const modal = screen.getByRole('dialog')
    expect(modal).toBeInTheDocument()

    // Completar con nombre duplicado dentro del modal
    await user.type(
      within(modal).getByLabelText(/nombre/i),
      'Manzanas Red Delicious',
    )
    await user.type(within(modal).getByLabelText(/precio base/i), '1200')
    await user.selectOptions(
      within(modal).getByLabelText(/unidad de venta/i),
      '1',
    )
    const stockInputDup = within(modal).getByLabelText(/stock disponible/i)
    await user.clear(stockInputDup)
    await user.type(stockInputDup, '10')
    await user.click(
      within(modal).getByRole('button', { name: /crear producto/i }),
    )

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
      const alert = screen.getByRole('alert')
      expect(alert).toBeInTheDocument()
      expect(alert).toHaveTextContent(
        "Ya existe un producto activo con el nombre 'Manzanas Red Delicious'.",
      )
    })
  })

  it('alterna la disponibilidad de un producto mediante PUT con payload invertido', async () => {
    const user = userEvent.setup()
    let producto1Disponibilidad = true

    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(async (input, init) => {
        const url = String(input)
        const method = init?.method ?? 'GET'

        if (url.endsWith('/api/v1/productos') && method === 'GET') {
          return new Response(
            JSON.stringify([
              {
                ...mockProductos[0],
                disponible: producto1Disponibilidad,
              },
              mockProductos[1],
            ]),
            { status: 200 },
          )
        }
        if (url.endsWith('/api/v1/unidades-medida') && method === 'GET') {
          return new Response(JSON.stringify(mockUnidades), { status: 200 })
        }
        if (url.endsWith('/api/v1/productos/1') && method === 'PUT') {
          const body = JSON.parse(String(init?.body)) as { disponible: boolean }
          producto1Disponibilidad = body.disponible
          return new Response(
            JSON.stringify({
              ...mockProductos[0],
              disponible: producto1Disponibilidad,
            }),
            { status: 200 },
          )
        }
        return new Response('Not Found', { status: 404 })
      })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Manzanas Red Delicious')).toBeInTheDocument()
    })

    // El primer botón de disponibilidad debe indicar Disponible (aria-pressed="true")
    const btnToggle = screen.getByRole('button', {
      name: /disponibilidad manzanas red delicious: pausar/i,
    })
    expect(btnToggle).toHaveAttribute('aria-pressed', 'true')

    await user.click(btnToggle)

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/productos/1'),
        expect.objectContaining({
          method: 'PUT',
          body: expect.stringContaining('"disponible":false'),
        }),
      )
    })
  })

  it('anula un producto mediante DELETE 204 y lo remueve de la lista sin recargar la página', async () => {
    const user = userEvent.setup()
    let productosActuales = [...mockProductos]

    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(async (input, init) => {
        const url = String(input)
        const method = init?.method ?? 'GET'

        if (url.endsWith('/api/v1/productos') && method === 'GET') {
          return new Response(JSON.stringify(productosActuales), {
            status: 200,
          })
        }
        if (url.endsWith('/api/v1/unidades-medida') && method === 'GET') {
          return new Response(JSON.stringify(mockUnidades), { status: 200 })
        }
        if (url.endsWith('/api/v1/productos/2') && method === 'DELETE') {
          productosActuales = productosActuales.filter((p) => p.id !== 2)
          return new Response(null, { status: 204 })
        }
        return new Response('Not Found', { status: 404 })
      })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Alfajor Artesanal')).toBeInTheDocument()
    })

    const btnAnular = screen.getByRole('button', {
      name: /anular alfajor artesanal/i,
    })
    await user.click(btnAnular)

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/productos/2'),
        expect.objectContaining({
          method: 'DELETE',
        }),
      )
      expect(screen.queryByText('Alfajor Artesanal')).not.toBeInTheDocument()
    })

    expect(screen.getByText('1 producto activo')).toBeInTheDocument()
  })

  it('edita un producto exitosamente mediante PUT y actualiza el catálogo', async () => {
    const user = userEvent.setup()
    const productoModificado: Producto = {
      ...mockProductos[0],
      precio_base: 1800,
    }
    let productosActuales = [...mockProductos]

    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(async (input, init) => {
        const url = String(input)
        const method = init?.method ?? 'GET'

        if (url.endsWith('/api/v1/productos') && method === 'GET') {
          return new Response(JSON.stringify(productosActuales), {
            status: 200,
          })
        }
        if (url.endsWith('/api/v1/unidades-medida') && method === 'GET') {
          return new Response(JSON.stringify(mockUnidades), { status: 200 })
        }
        if (url.endsWith('/api/v1/productos/1') && method === 'PUT') {
          productosActuales = productosActuales.map((p) =>
            p.id === 1 ? productoModificado : p,
          )
          return new Response(JSON.stringify(productoModificado), {
            status: 200,
          })
        }
        return new Response('Not Found', { status: 404 })
      })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Manzanas Red Delicious')).toBeInTheDocument()
    })

    // Abrir modal de edición para el primer producto
    const btnEditar = screen.getByRole('button', {
      name: /editar manzanas red delicious/i,
    })
    await user.click(btnEditar)

    const modal = screen.getByRole('dialog', { name: /editar producto/i })
    expect(modal).toBeInTheDocument()

    // Modificar precio base
    const precioInput = within(modal).getByLabelText(/precio base/i)
    const stockInput = within(modal).getByLabelText(/stock disponible/i)
    expect((stockInput as HTMLInputElement).value).toBe('25.5')
    await user.clear(precioInput)
    await user.type(precioInput, '1800')

    // Guardar cambios
    const btnGuardar = within(modal).getByRole('button', {
      name: /guardar cambios/i,
    })
    await user.click(btnGuardar)

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/productos/1'),
        expect.objectContaining({
          method: 'PUT',
          body: expect.stringContaining('"precio_base":1800'),
        }),
      )
    })
  })

  it('normaliza valores de stock y precio al abrir edición de producto con escala decimal de API y al cambiar a unidad contable', async () => {
    const user = userEvent.setup()
    const productoDecimal = {
      id: 3,
      nombre: 'Harina 000',
      descripcion: 'Harina de trigo',
      precio_base: '1250.00' as unknown as number,
      unidad_venta_id: 1,
      unidad_venta: mockUnidades[0],
      stock_cantidad: '30.000' as unknown as number,
      disponible: true,
      activo: true,
      anulado_at: null,
      hay_stock: true,
      categorias: [],
    }

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.endsWith('/api/v1/productos')) {
        return new Response(JSON.stringify([productoDecimal]), { status: 200 })
      }
      if (url.endsWith('/api/v1/unidades-medida')) {
        return new Response(JSON.stringify(mockUnidades), { status: 200 })
      }
      return new Response('Not Found', { status: 404 })
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Harina 000')).toBeInTheDocument()
    })

    const btnEditar = screen.getByRole('button', {
      name: /editar harina 000/i,
    })
    await user.click(btnEditar)

    const modal = screen.getByRole('dialog', { name: /editar producto/i })
    const precioInput = within(modal).getByLabelText(/precio base/i)
    const stockInput = within(modal).getByLabelText(/stock disponible/i)

    expect((precioInput as HTMLInputElement).value).toBe('1250')
    expect((stockInput as HTMLInputElement).value).toBe('30')

    const selectUnidad = within(modal).getByLabelText(/unidad de venta/i)
    await user.selectOptions(selectUnidad, '2')
    expect((stockInput as HTMLInputElement).value).toBe('30')
  })

  it('reintenta la carga del catálogo al hacer clic en Reintentar tras un fallo inicial', async () => {
    const user = userEvent.setup()
    let intento = 0

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (intento === 0) {
        return new Response(
          JSON.stringify({ detail: 'Error temporal en el servicio de catálogo.' }),
          { status: 500, headers: { 'Content-Type': 'application/json' } },
        )
      }

      if (url.endsWith('/api/v1/productos')) {
        return new Response(JSON.stringify(mockProductos), { status: 200 })
      }
      if (url.endsWith('/api/v1/unidades-medida')) {
        return new Response(JSON.stringify(mockUnidades), { status: 200 })
      }
      return new Response('Not Found', { status: 404 })
    })

    render(<App />)

    const alertSection = await screen.findByRole('alert')
    expect(alertSection).toBeInTheDocument()
    expect(
      screen.getByText('Error temporal en el servicio de catálogo.'),
    ).toBeInTheDocument()

    const btnReintentar = screen.getByRole('button', { name: /reintentar/i })
    expect(btnReintentar).toBeInTheDocument()

    // Segundo intento exitoso
    intento = 1
    await user.click(btnReintentar)

    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
      expect(screen.getByText('Manzanas Red Delicious')).toBeInTheDocument()
      expect(screen.getByText('Alfajor Artesanal')).toBeInTheDocument()
    })
  })

  it('abre el modal desde el botón de catálogo vacío (+ Crear primer producto) y lo cierra con Escape', async () => {
    const user = userEvent.setup()

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.endsWith('/api/v1/productos')) {
        return new Response(JSON.stringify([]), { status: 200 })
      }
      if (url.endsWith('/api/v1/unidades-medida')) {
        return new Response(JSON.stringify(mockUnidades), { status: 200 })
      }
      return new Response('Not Found', { status: 404 })
    })

    render(<App />)

    await waitFor(() => {
      expect(
        screen.getByText('No hay productos registrados en el catálogo'),
      ).toBeInTheDocument()
    })

    const btnCrearPrimer = screen.getByRole('button', {
      name: '+ Crear primer producto',
    })
    await user.click(btnCrearPrimer)

    const modal = screen.getByRole('dialog', { name: 'Nuevo Producto' })
    expect(modal).toBeInTheDocument()

    fireEvent.keyDown(document, { key: 'Escape' })

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })

  it('muestra alerta de error si falla la petición de cambio de disponibilidad o de anulación', async () => {
    const user = userEvent.setup()

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      const method = init?.method ?? 'GET'

      if (url.endsWith('/api/v1/productos') && method === 'GET') {
        return new Response(JSON.stringify(mockProductos), { status: 200 })
      }
      if (url.endsWith('/api/v1/unidades-medida') && method === 'GET') {
        return new Response(JSON.stringify(mockUnidades), { status: 200 })
      }
      if (url.includes('/api/v1/productos/1') && method === 'PUT') {
        return new Response(
          JSON.stringify({
            detail: 'No se puede pausar un producto en promoción vigente (conflicto 409).',
          }),
          { status: 409, headers: { 'Content-Type': 'application/json' } },
        )
      }
      if (url.includes('/api/v1/productos/2') && method === 'DELETE') {
        return new Response(
          JSON.stringify({
            detail: 'No se puede anular un producto con pedidos pendientes.',
          }),
          { status: 409, headers: { 'Content-Type': 'application/json' } },
        )
      }
      return new Response('Not Found', { status: 404 })
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Manzanas Red Delicious')).toBeInTheDocument()
    })

    // Fallo en toggle de disponibilidad
    const btnToggle = screen.getByRole('button', {
      name: 'Disponibilidad Manzanas Red Delicious: Pausar',
    })
    await user.click(btnToggle)

    const alertDisp = await screen.findByRole('alert')
    expect(alertDisp).toBeInTheDocument()
    expect(
      screen.getByText(
        'No se puede pausar un producto en promoción vigente (conflicto 409).',
      ),
    ).toBeInTheDocument()

    // Reintentar para restaurar catálogo
    const btnReintentar = screen.getByRole('button', { name: /reintentar/i })
    await user.click(btnReintentar)

    await waitFor(() => {
      expect(screen.getByText('Alfajor Artesanal')).toBeInTheDocument()
    })

    // Fallo en anulación
    const btnAnular = screen.getByRole('button', {
      name: 'Anular Alfajor Artesanal',
    })
    await user.click(btnAnular)

    const alertAnular = await screen.findByRole('alert')
    expect(alertAnular).toBeInTheDocument()
    expect(
      screen.getByText('No se puede anular un producto con pedidos pendientes.'),
    ).toBeInTheDocument()
  })
})
