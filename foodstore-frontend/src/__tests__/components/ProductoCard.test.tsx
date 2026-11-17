// Consigna: docs/consignas_examen_2.md, 4/R4 y 7/HU-P2-03 — Pruebas unitarias de formateadores y tarjeta accesible ProductoCard.

import { describe, it, expect, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  ProductoCard,
  formatearPrecio,
  formatearStock,
} from '../../components/ProductoCard'
import type { Producto, UnidadMedida } from '../../types'

describe('formatearPrecio y formatearStock', () => {
  describe('formatearPrecio', () => {
    it('formatea números enteros con dos decimales y coma', () => {
      expect(formatearPrecio(1500)).toBe('1500,00')
      expect(formatearPrecio(0)).toBe('0,00')
    })

    it('formatea valores decimales a dos posiciones con coma', () => {
      expect(formatearPrecio(12.5)).toBe('12,50')
      expect(formatearPrecio(99.99)).toBe('99,99')
    })

    it('formatea cadenas numéricas válidas', () => {
      expect(formatearPrecio('1250.75')).toBe('1250,75')
      expect(formatearPrecio('100')).toBe('100,00')
    })

    it('retorna 0,00 para valores no finitos o inválidos', () => {
      expect(formatearPrecio(Number.NaN)).toBe('0,00')
      expect(formatearPrecio('abc')).toBe('0,00')
      expect(formatearPrecio(Infinity)).toBe('0,00')
    })
  })

  describe('formatearStock', () => {
    it('formatea números enteros sin decimales superfluos', () => {
      expect(formatearStock(25)).toBe('25')
      expect(formatearStock(0)).toBe('0')
      expect(formatearStock('30.000')).toBe('30')
    })

    it('formatea decimales hasta 3 posiciones suprimiendo ceros finales redundantes', () => {
      expect(formatearStock(25.5)).toBe('25,5')
      expect(formatearStock(3.125)).toBe('3,125')
      expect(formatearStock('1.500')).toBe('1,5')
      expect(formatearStock(0.1)).toBe('0,1')
    })

    it('retorna 0 para valores no finitos o inválidos', () => {
      expect(formatearStock(Number.NaN)).toBe('0')
      expect(formatearStock('abc')).toBe('0')
      expect(formatearStock(Infinity)).toBe('0')
    })
  })
})

describe('ProductoCard Component', () => {
  const unidadKg: UnidadMedida = {
    id: 1,
    nombre: 'Kilogramo',
    simbolo: 'kg',
    tipo: 'peso',
  }

  const productoBase: Producto = {
    id: 10,
    nombre: 'Manzanas Red Delicious',
    descripcion: 'Manzanas rojas seleccionadas de primera calidad.',
    precio_base: 1500.5,
    unidad_venta_id: 1,
    unidad_venta: unidadKg,
    stock_cantidad: 25.5,
    disponible: true,
    activo: true,
    anulado_at: null,
    hay_stock: true,
    categorias: [
      { id: 101, nombre: 'Frutas', descripcion: null, activo: true, anulado_at: null },
      { id: 102, nombre: 'Frescos', descripcion: null, activo: true, anulado_at: null },
    ],
  }

  it('renderiza estructura accesible article vinculada por aria-labelledby con datos completos', () => {
    render(
      <ProductoCard
        producto={productoBase}
        onEditar={vi.fn()}
        onToggleDisponibilidad={vi.fn()}
        onAnular={vi.fn()}
      />,
    )

    const article = screen.getByRole('article', {
      name: 'Manzanas Red Delicious',
    })
    expect(article).toBeInTheDocument()
    expect(article).toHaveAttribute('aria-labelledby', 'producto-titulo-10')

    const titulo = screen.getByRole('heading', {
      level: 3,
      name: 'Manzanas Red Delicious',
    })
    expect(titulo).toHaveAttribute('id', 'producto-titulo-10')

    // Unidad en badge
    expect(screen.getByText('Kilogramo (kg)')).toBeInTheDocument()

    // Descripción
    expect(
      screen.getByText('Manzanas rojas seleccionadas de primera calidad.'),
    ).toBeInTheDocument()

    // Precio visible y aria-label accesible
    const precioEl = screen.getByLabelText('Precio base: $ 1500,50 por kg')
    expect(precioEl).toBeInTheDocument()
    expect(precioEl).toHaveTextContent('$ 1500,50 / kg')

    // Stock visible y aria-label accesible
    const stockEl = screen.getByLabelText('Stock disponible: 25,5 kg')
    expect(stockEl).toBeInTheDocument()
    expect(stockEl).toHaveTextContent('stock: 25,5 kg')
  })

  it('muestra texto alternativo "Sin descripción" cuando descripcion es null o vacía', () => {
    const productoSinDesc: Producto = {
      ...productoBase,
      descripcion: null,
    }

    render(
      <ProductoCard
        producto={productoSinDesc}
        onEditar={vi.fn()}
        onToggleDisponibilidad={vi.fn()}
        onAnular={vi.fn()}
      />,
    )

    expect(screen.getByText('Sin descripción')).toBeInTheDocument()
  })

  it('renderiza indicadores de disponibilidad y stock de forma independiente en grupo de estados (RN-11 y RN-12)', () => {
    // Caso 1: disponible y con stock
    const { rerender } = render(
      <ProductoCard
        producto={productoBase}
        onEditar={vi.fn()}
        onToggleDisponibilidad={vi.fn()}
        onAnular={vi.fn()}
      />,
    )

    const grupoEstados1 = screen.getByRole('group', {
      name: 'Estados del producto',
    })
    expect(within(grupoEstados1).getByText('Disponible')).toBeInTheDocument()
    expect(within(grupoEstados1).getByText('Hay stock')).toBeInTheDocument()

    // Caso 2: no disponible pero con stock
    rerender(
      <ProductoCard
        producto={{ ...productoBase, disponible: false, hay_stock: true }}
        onEditar={vi.fn()}
        onToggleDisponibilidad={vi.fn()}
        onAnular={vi.fn()}
      />,
    )

    const grupoEstados2 = screen.getByRole('group', {
      name: 'Estados del producto',
    })
    expect(within(grupoEstados2).getByText('No disponible')).toBeInTheDocument()
    expect(within(grupoEstados2).getByText('Hay stock')).toBeInTheDocument()

    // Caso 3: disponible pero sin stock (RN-12)
    rerender(
      <ProductoCard
        producto={{
          ...productoBase,
          disponible: true,
          hay_stock: false,
          stock_cantidad: 0,
        }}
        onEditar={vi.fn()}
        onToggleDisponibilidad={vi.fn()}
        onAnular={vi.fn()}
      />,
    )

    const grupoEstados3 = screen.getByRole('group', {
      name: 'Estados del producto',
    })
    expect(within(grupoEstados3).getByText('Disponible')).toBeInTheDocument()
    expect(within(grupoEstados3).getByText('Sin stock')).toBeInTheDocument()
  })

  it('renderiza lista accesible de categorías cuando tiene elementos y la omite cuando está vacía', () => {
    const { rerender } = render(
      <ProductoCard
        producto={productoBase}
        onEditar={vi.fn()}
        onToggleDisponibilidad={vi.fn()}
        onAnular={vi.fn()}
      />,
    )

    const listaCategorias = screen.getByRole('list', {
      name: 'Categorías del producto',
    })
    expect(listaCategorias).toBeInTheDocument()
    const items = within(listaCategorias).getAllByRole('listitem')
    expect(items).toHaveLength(2)
    expect(within(listaCategorias).getByText('Frutas')).toBeInTheDocument()
    expect(within(listaCategorias).getByText('Frescos')).toBeInTheDocument()

    // Caso con categorías vacías
    rerender(
      <ProductoCard
        producto={{ ...productoBase, categorias: [] }}
        onEditar={vi.fn()}
        onToggleDisponibilidad={vi.fn()}
        onAnular={vi.fn()}
      />,
    )

    expect(
      screen.queryByRole('list', { name: 'Categorías del producto' }),
    ).not.toBeInTheDocument()
  })

  it('ejecuta callbacks al presionar los botones de acción en el footer', async () => {
    const user = userEvent.setup()
    const onEditarMock = vi.fn()
    const onToggleMock = vi.fn()
    const onAnularMock = vi.fn()

    const { rerender } = render(
      <ProductoCard
        producto={productoBase}
        onEditar={onEditarMock}
        onToggleDisponibilidad={onToggleMock}
        onAnular={onAnularMock}
      />,
    )

    const footer = screen.getByRole('group', {
      name: `Acciones para ${productoBase.nombre}`,
    })
    expect(footer).toBeInTheDocument()

    // Botón Editar
    const btnEditar = within(footer).getByRole('button', {
      name: `Editar ${productoBase.nombre}`,
    })
    await user.click(btnEditar)
    expect(onEditarMock).toHaveBeenCalledWith(productoBase)

    // Botón Disponibilidad (Pausar cuando disponible=true, aria-pressed="true")
    const btnToggle = within(footer).getByRole('button', {
      name: `Disponibilidad ${productoBase.nombre}: Pausar`,
    })
    expect(btnToggle).toHaveAttribute('aria-pressed', 'true')
    await user.click(btnToggle)
    expect(onToggleMock).toHaveBeenCalledWith(productoBase)

    // Botón Anular
    const btnAnular = within(footer).getByRole('button', {
      name: `Anular ${productoBase.nombre}`,
    })
    await user.click(btnAnular)
    expect(onAnularMock).toHaveBeenCalledWith(productoBase)

    // Verificar botón Disponibilidad cuando disponible=false (Activar, aria-pressed="false")
    rerender(
      <ProductoCard
        producto={{ ...productoBase, disponible: false }}
        onEditar={onEditarMock}
        onToggleDisponibilidad={onToggleMock}
        onAnular={onAnularMock}
      />,
    )

    const btnActivar = screen.getByRole('button', {
      name: `Disponibilidad ${productoBase.nombre}: Activar`,
    })
    expect(btnActivar).toHaveAttribute('aria-pressed', 'false')
  })

  it('deshabilita todos los botones de acción cuando disabled=true', async () => {
    const user = userEvent.setup()
    const onEditarMock = vi.fn()
    const onToggleMock = vi.fn()
    const onAnularMock = vi.fn()

    render(
      <ProductoCard
        producto={productoBase}
        onEditar={onEditarMock}
        onToggleDisponibilidad={onToggleMock}
        onAnular={onAnularMock}
        disabled={true}
      />,
    )

    const btnEditar = screen.getByRole('button', {
      name: `Editar ${productoBase.nombre}`,
    })
    const btnToggle = screen.getByRole('button', {
      name: `Disponibilidad ${productoBase.nombre}: Pausar`,
    })
    const btnAnular = screen.getByRole('button', {
      name: `Anular ${productoBase.nombre}`,
    })

    expect(btnEditar).toBeDisabled()
    expect(btnToggle).toBeDisabled()
    expect(btnAnular).toBeDisabled()

    await user.click(btnEditar)
    await user.click(btnToggle)
    await user.click(btnAnular)

    expect(onEditarMock).not.toHaveBeenCalled()
    expect(onToggleMock).not.toHaveBeenCalled()
    expect(onAnularMock).not.toHaveBeenCalled()
  })
})
