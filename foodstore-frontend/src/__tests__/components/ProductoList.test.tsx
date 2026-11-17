// Consigna: docs/consignas_examen_2.md, 4/R4 y 7/HU-P2-03 — Pruebas unitarias de ProductoList y estado vacío accesible.

import { describe, it, expect, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ProductoList } from '../../components/ProductoList'
import type { Producto, UnidadMedida } from '../../types'

describe('ProductoList Component', () => {
  const unidadKg: UnidadMedida = {
    id: 1,
    nombre: 'Kilogramo',
    simbolo: 'kg',
    tipo: 'peso',
  }

  const unidadU: UnidadMedida = {
    id: 2,
    nombre: 'Unidad',
    simbolo: 'u',
    tipo: 'contable',
  }

  const mockProductos: Producto[] = [
    {
      id: 1,
      nombre: 'Manzanas Red Delicious',
      descripcion: 'Manzanas rojas seleccionadas',
      precio_base: 1500.5,
      unidad_venta_id: 1,
      unidad_venta: unidadKg,
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
      unidad_venta: unidadU,
      stock_cantidad: 0,
      disponible: false,
      activo: true,
      anulado_at: null,
      hay_stock: false,
      categorias: [],
    },
  ]

  describe('Estado vacío', () => {
    it('renderiza la sección accesible de catálogo vacío y mensaje explicativo', () => {
      render(
        <ProductoList
          productos={[]}
          onEditar={vi.fn()}
          onToggleDisponibilidad={vi.fn()}
          onAnular={vi.fn()}
        />,
      )

      const emptySection = screen.getByRole('region', {
        name: 'Catálogo de productos vacío',
      })
      expect(emptySection).toBeInTheDocument()

      expect(
        screen.getByRole('heading', {
          level: 2,
          name: 'No hay productos registrados en el catálogo',
        }),
      ).toBeInTheDocument()

      expect(
        screen.getByText(
          /Agregá el primer producto para comenzar a administrar precios/i,
        ),
      ).toBeInTheDocument()

      // Si no se provee onNuevoProducto, no debe renderizarse el botón
      expect(
        screen.queryByRole('button', { name: '+ Crear primer producto' }),
      ).not.toBeInTheDocument()
    })

    it('renderiza el botón "+ Crear primer producto" cuando se provee onNuevoProducto y ejecuta el callback', async () => {
      const user = userEvent.setup()
      const onNuevoProductoMock = vi.fn()

      render(
        <ProductoList
          productos={[]}
          onEditar={vi.fn()}
          onToggleDisponibilidad={vi.fn()}
          onAnular={vi.fn()}
          onNuevoProducto={onNuevoProductoMock}
        />,
      )

      const btnCrearPrimer = screen.getByRole('button', {
        name: '+ Crear primer producto',
      })
      expect(btnCrearPrimer).toBeInTheDocument()
      expect(btnCrearPrimer).toBeEnabled()

      await user.click(btnCrearPrimer)
      expect(onNuevoProductoMock).toHaveBeenCalledTimes(1)
    })

    it('deshabilita el botón de crear primer producto cuando disabled=true', async () => {
      const user = userEvent.setup()
      const onNuevoProductoMock = vi.fn()

      render(
        <ProductoList
          productos={[]}
          onEditar={vi.fn()}
          onToggleDisponibilidad={vi.fn()}
          onAnular={vi.fn()}
          onNuevoProducto={onNuevoProductoMock}
          disabled={true}
        />,
      )

      const btnCrearPrimer = screen.getByRole('button', {
        name: '+ Crear primer producto',
      })
      expect(btnCrearPrimer).toBeDisabled()

      await user.click(btnCrearPrimer)
      expect(onNuevoProductoMock).not.toHaveBeenCalled()
    })
  })

  describe('Listado con productos', () => {
    it('renderiza la sección accesible de listado y mapea cada producto en una tarjeta', () => {
      render(
        <ProductoList
          productos={mockProductos}
          onEditar={vi.fn()}
          onToggleDisponibilidad={vi.fn()}
          onAnular={vi.fn()}
        />,
      )

      const listSection = screen.getByRole('region', {
        name: 'Listado de productos del catálogo',
      })
      expect(listSection).toBeInTheDocument()

      const articulos = screen.getAllByRole('article')
      expect(articulos).toHaveLength(2)

      expect(screen.getByText('Manzanas Red Delicious')).toBeInTheDocument()
      expect(screen.getByText('Alfajor Artesanal')).toBeInTheDocument()
    })

    it('propaga callbacks de acción a las tarjetas hijas', async () => {
      const user = userEvent.setup()
      const onEditarMock = vi.fn()
      const onToggleMock = vi.fn()
      const onAnularMock = vi.fn()

      render(
        <ProductoList
          productos={mockProductos}
          onEditar={onEditarMock}
          onToggleDisponibilidad={onToggleMock}
          onAnular={onAnularMock}
        />,
      )

      // Tarjeta 1: Editar
      const btnEditar1 = screen.getByRole('button', {
        name: 'Editar Manzanas Red Delicious',
      })
      await user.click(btnEditar1)
      expect(onEditarMock).toHaveBeenCalledWith(mockProductos[0])

      // Tarjeta 1: Disponibilidad
      const btnToggle1 = screen.getByRole('button', {
        name: 'Disponibilidad Manzanas Red Delicious: Pausar',
      })
      await user.click(btnToggle1)
      expect(onToggleMock).toHaveBeenCalledWith(mockProductos[0])

      // Tarjeta 2: Anular
      const btnAnular2 = screen.getByRole('button', {
        name: 'Anular Alfajor Artesanal',
      })
      await user.click(btnAnular2)
      expect(onAnularMock).toHaveBeenCalledWith(mockProductos[1])
    })

    it('propaga prop disabled={true} a todas las tarjetas del listado', () => {
      render(
        <ProductoList
          productos={mockProductos}
          onEditar={vi.fn()}
          onToggleDisponibilidad={vi.fn()}
          onAnular={vi.fn()}
          disabled={true}
        />,
      )

      const articulos = screen.getAllByRole('article')
      for (const articulo of articulos) {
        const botones = within(articulo).getAllByRole('button')
        for (const boton of botones) {
          expect(boton).toBeDisabled()
        }
      }
    })
  })
})
