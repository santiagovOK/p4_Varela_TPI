// Consigna: docs/consignas_examen_2.md, 3.4/RN-01, RN-02, RN-10, 4/R4 y 7/HU-P2-03 — Pruebas unitarias y de accesibilidad de ProductoModal.

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  ProductoModal,
  validarFormularioProducto,
} from '../../components/ProductoModal'
import { VALIDATION_MESSAGES } from '../../constants/validationMessages'
import type { Producto, UnidadMedida } from '../../types'

describe('validarFormularioProducto', () => {
  const unidadesMock: UnidadMedida[] = [
    { id: 1, nombre: 'Kilogramo', simbolo: 'kg', tipo: 'peso' },
    { id: 2, nombre: 'Unidad', simbolo: 'u', tipo: 'contable' },
    { id: 3, nombre: 'Litro', simbolo: 'l', tipo: 'volumen' },
  ]

  const valoresValidos = {
    nombre: 'Milanesa con papas',
    descripcion: 'Plato clásico',
    precio_base: '2500',
    unidad_venta_id: '1',
    stock_cantidad: '10.5',
    disponible: true,
  }

  describe('Regla RN-01: Campos obligatorios y rangos válidos', () => {
    it('detecta nombre obligatorio o solo espacios', () => {
      const err1 = validarFormularioProducto(
        { ...valoresValidos, nombre: '' },
        unidadesMock,
      )
      expect(err1.nombre).toBe(VALIDATION_MESSAGES.NOMBRE_REQUIRED)

      const err2 = validarFormularioProducto(
        { ...valoresValidos, nombre: '   ' },
        unidadesMock,
      )
      expect(err2.nombre).toBe(VALIDATION_MESSAGES.NOMBRE_REQUIRED)
    })

    it('detecta nombre con menos de 3 caracteres', () => {
      const err = validarFormularioProducto(
        { ...valoresValidos, nombre: 'ab' },
        unidadesMock,
      )
      expect(err.nombre).toBe(VALIDATION_MESSAGES.NOMBRE_MIN_LENGTH)
    })

    it('detecta precio obligatorio, no numérico y negativo', () => {
      const errVacio = validarFormularioProducto(
        { ...valoresValidos, precio_base: '' },
        unidadesMock,
      )
      expect(errVacio.precio_base).toBe(VALIDATION_MESSAGES.PRECIO_REQUIRED)

      const errInvalido = validarFormularioProducto(
        { ...valoresValidos, precio_base: 'abc' },
        unidadesMock,
      )
      expect(errInvalido.precio_base).toBe(VALIDATION_MESSAGES.INVALID_NUMBER)

      const errNegativo = validarFormularioProducto(
        { ...valoresValidos, precio_base: '-10' },
        unidadesMock,
      )
      expect(errNegativo.precio_base).toBe(VALIDATION_MESSAGES.PRECIO_NON_NEGATIVE)
    })

    it('detecta unidad de venta vacía, cero o inválida', () => {
      const errVacio = validarFormularioProducto(
        { ...valoresValidos, unidad_venta_id: '' },
        unidadesMock,
      )
      expect(errVacio.unidad_venta_id).toBe(VALIDATION_MESSAGES.UNIDAD_REQUIRED)

      const errCero = validarFormularioProducto(
        { ...valoresValidos, unidad_venta_id: '0' },
        unidadesMock,
      )
      expect(errCero.unidad_venta_id).toBe(VALIDATION_MESSAGES.UNIDAD_REQUIRED)

      const errInvalido = validarFormularioProducto(
        { ...valoresValidos, unidad_venta_id: 'abc' },
        unidadesMock,
      )
      expect(errInvalido.unidad_venta_id).toBe(VALIDATION_MESSAGES.UNIDAD_REQUIRED)
    })

    it('detecta stock obligatorio, no numérico y negativo', () => {
      const errVacio = validarFormularioProducto(
        { ...valoresValidos, stock_cantidad: '' },
        unidadesMock,
      )
      expect(errVacio.stock_cantidad).toBe(VALIDATION_MESSAGES.STOCK_REQUIRED)

      const errInvalido = validarFormularioProducto(
        { ...valoresValidos, stock_cantidad: 'no-numero' },
        unidadesMock,
      )
      expect(errInvalido.stock_cantidad).toBe(VALIDATION_MESSAGES.INVALID_NUMBER)

      const errNegativo = validarFormularioProducto(
        { ...valoresValidos, stock_cantidad: '-1' },
        unidadesMock,
      )
      expect(errNegativo.stock_cantidad).toBe(VALIDATION_MESSAGES.STOCK_NON_NEGATIVE)
    })
  })

  describe('Regla RN-10: Restricción de stock entero para unidades contables', () => {
    it('rechaza stock fraccionario o decimal para unidades contables (con punto o coma)', () => {
      const errPunto = validarFormularioProducto(
        { ...valoresValidos, unidad_venta_id: '2', stock_cantidad: '2.5' },
        unidadesMock,
      )
      expect(errPunto.stock_cantidad).toBe(
        VALIDATION_MESSAGES.STOCK_INTEGER_FOR_CONTABLE,
      )

      const errComa = validarFormularioProducto(
        { ...valoresValidos, unidad_venta_id: '2', stock_cantidad: '2,5' },
        unidadesMock,
      )
      expect(errComa.stock_cantidad).toBe(
        VALIDATION_MESSAGES.STOCK_INTEGER_FOR_CONTABLE,
      )
    })

    it('acepta stock entero para unidades contables', () => {
      const errEntero = validarFormularioProducto(
        { ...valoresValidos, unidad_venta_id: '2', stock_cantidad: '5' },
        unidadesMock,
      )
      expect(errEntero).toEqual({})

      const errCero = validarFormularioProducto(
        { ...valoresValidos, unidad_venta_id: '2', stock_cantidad: '0' },
        unidadesMock,
      )
      expect(errCero).toEqual({})
    })

    it('acepta stock decimal para unidades de peso o volumen', () => {
      // Unidad peso (kg)
      const errPeso = validarFormularioProducto(
        { ...valoresValidos, unidad_venta_id: '1', stock_cantidad: '2.5' },
        unidadesMock,
      )
      expect(errPeso).toEqual({})

      // Unidad volumen (l)
      const errVolumen = validarFormularioProducto(
        { ...valoresValidos, unidad_venta_id: '3', stock_cantidad: '0.125' },
        unidadesMock,
      )
      expect(errVolumen).toEqual({})
    })
  })
})

describe('ProductoModal Component', () => {
  const unidadesMock: UnidadMedida[] = [
    { id: 1, nombre: 'Kilogramo', simbolo: 'kg', tipo: 'peso' },
    { id: 2, nombre: 'Unidad', simbolo: 'u', tipo: 'contable' },
  ]

  const productoMock: Producto = {
    id: 42,
    nombre: 'Café de Especialidad',
    descripcion: 'Granos tostados 250g',
    precio_base: '1500.00' as unknown as number,
    unidad_venta_id: 1,
    unidad_venta: unidadesMock[0],
    stock_cantidad: '30.000' as unknown as number,
    disponible: true,
    activo: true,
    anulado_at: null,
    hay_stock: true,
    categorias: [],
  }

  it('no renderiza nada en el DOM cuando isOpen={false}', () => {
    const { container } = render(
      <ProductoModal
        isOpen={false}
        unidades={unidadesMock}
        onGuardar={vi.fn()}
        onCerrar={vi.fn()}
      />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('renderiza modo alta con role="dialog", aria-modal="true", título "Nuevo Producto" y foco inicial en el nombre', () => {
    render(
      <ProductoModal
        isOpen={true}
        productoSeleccionado={null}
        unidades={unidadesMock}
        onGuardar={vi.fn()}
        onCerrar={vi.fn()}
      />,
    )

    const dialog = screen.getByRole('dialog', { name: 'Nuevo Producto' })
    expect(dialog).toBeInTheDocument()
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(dialog).toHaveAttribute('aria-labelledby', 'producto-modal-titulo')

    const btnSubmit = screen.getByRole('button', { name: 'Crear producto' })
    expect(btnSubmit).toBeInTheDocument()

    const inputNombre = screen.getByLabelText('Nombre del producto')
    expect(document.activeElement).toBe(inputNombre)
  })

  it('renderiza modo edición con título "Editar Producto", botón "Guardar cambios" y valores normalizados', () => {
    render(
      <ProductoModal
        isOpen={true}
        productoSeleccionado={productoMock}
        unidades={unidadesMock}
        onGuardar={vi.fn()}
        onCerrar={vi.fn()}
      />,
    )

    const dialog = screen.getByRole('dialog', { name: 'Editar Producto' })
    expect(dialog).toBeInTheDocument()

    const btnSubmit = screen.getByRole('button', { name: 'Guardar cambios' })
    expect(btnSubmit).toBeInTheDocument()

    const inputNombre = screen.getByLabelText('Nombre del producto') as HTMLInputElement
    const inputPrecio = screen.getByLabelText('Precio base ($)') as HTMLInputElement
    const selectUnidad = screen.getByLabelText('Unidad de venta') as HTMLSelectElement
    const inputStock = screen.getByLabelText('Stock disponible') as HTMLInputElement

    expect(inputNombre.value).toBe('Café de Especialidad')
    // Normalizados sin ceros redundantes
    expect(inputPrecio.value).toBe('1500')
    expect(selectUnidad.value).toBe('1')
    expect(inputStock.value).toBe('30')
  })

  describe('Accesibilidad de teclado y trampa de foco en modal', () => {
    it('cicla el foco al primer botón al presionar Tab desde el último botón habilitado', () => {
      render(
        <ProductoModal
          isOpen={true}
          productoSeleccionado={null}
          unidades={unidadesMock}
          onGuardar={vi.fn()}
          onCerrar={vi.fn()}
        />,
      )

      const btnCerrar = screen.getByRole('button', { name: 'Cerrar modal' })
      const btnCrear = screen.getByRole('button', { name: 'Crear producto' })

      // Enfocar el último elemento accionable
      btnCrear.focus()
      expect(document.activeElement).toBe(btnCrear)

      // Simular evento Tab
      fireEvent.keyDown(document, { key: 'Tab' })
      expect(document.activeElement).toBe(btnCerrar)
    })

    it('cicla el foco al último botón al presionar Shift+Tab desde el primer botón', () => {
      render(
        <ProductoModal
          isOpen={true}
          productoSeleccionado={null}
          unidades={unidadesMock}
          onGuardar={vi.fn()}
          onCerrar={vi.fn()}
        />,
      )

      const btnCerrar = screen.getByRole('button', { name: 'Cerrar modal' })
      const btnCrear = screen.getByRole('button', { name: 'Crear producto' })

      // Enfocar el primer elemento accionable
      btnCerrar.focus()
      expect(document.activeElement).toBe(btnCerrar)

      // Simular evento Shift+Tab
      fireEvent.keyDown(document, { key: 'Tab', shiftKey: true })
      expect(document.activeElement).toBe(btnCrear)
    })

    it('cierra el modal al presionar Escape cuando isSaving={false}', () => {
      const onCerrarMock = vi.fn()
      render(
        <ProductoModal
          isOpen={true}
          unidades={unidadesMock}
          onGuardar={vi.fn()}
          onCerrar={onCerrarMock}
          isSaving={false}
        />,
      )

      fireEvent.keyDown(document, { key: 'Escape' })
      expect(onCerrarMock).toHaveBeenCalledTimes(1)
    })

    it('NO cierra el modal al presionar Escape cuando isSaving={true}', () => {
      const onCerrarMock = vi.fn()
      render(
        <ProductoModal
          isOpen={true}
          unidades={unidadesMock}
          onGuardar={vi.fn()}
          onCerrar={onCerrarMock}
          isSaving={true}
        />,
      )

      fireEvent.keyDown(document, { key: 'Escape' })
      expect(onCerrarMock).not.toHaveBeenCalled()
    })

    it('cierra el modal al hacer clic en el backdrop exterior pero no al hacer clic dentro del diálogo', () => {
      const onCerrarMock = vi.fn()
      const { container } = render(
        <ProductoModal
          isOpen={true}
          unidades={unidadesMock}
          onGuardar={vi.fn()}
          onCerrar={onCerrarMock}
          isSaving={false}
        />,
      )

      const overlay = container.firstChild as HTMLElement
      const dialog = screen.getByRole('dialog')

      // Clic dentro del diálogo no debe invocar onCerrar
      fireEvent.mouseDown(dialog)
      expect(onCerrarMock).not.toHaveBeenCalled()

      // Clic en el backdrop exterior sí debe invocar onCerrar
      fireEvent.mouseDown(overlay)
      expect(onCerrarMock).toHaveBeenCalledTimes(1)
    })
  })

  describe('Validación interactiva y atributos de accesibilidad', () => {
    it('marca campos inválidos con aria-invalid="true" y los vincula mediante aria-describedby al enviar formulario vacío', async () => {
      const user = userEvent.setup()
      const onGuardarMock = vi.fn()

      render(
        <ProductoModal
          isOpen={true}
          unidades={unidadesMock}
          onGuardar={onGuardarMock}
          onCerrar={vi.fn()}
        />,
      )

      const btnSubmit = screen.getByRole('button', { name: 'Crear producto' })
      await user.click(btnSubmit)

      expect(onGuardarMock).not.toHaveBeenCalled()

      // Validar input Nombre
      const inputNombre = screen.getByLabelText('Nombre del producto')
      expect(inputNombre).toHaveAttribute('aria-invalid', 'true')
      expect(inputNombre).toHaveAttribute('aria-describedby', 'error-producto-nombre')
      const msgNombre = screen.getByText(VALIDATION_MESSAGES.NOMBRE_REQUIRED)
      expect(msgNombre).toHaveAttribute('id', 'error-producto-nombre')

      // Validar input Precio
      const inputPrecio = screen.getByLabelText('Precio base ($)')
      expect(inputPrecio).toHaveAttribute('aria-invalid', 'true')
      expect(inputPrecio).toHaveAttribute(
        'aria-describedby',
        'error-producto-precio-base',
      )
      const msgPrecio = screen.getByText(VALIDATION_MESSAGES.PRECIO_REQUIRED)
      expect(msgPrecio).toHaveAttribute('id', 'error-producto-precio-base')

      // Validar select Unidad
      const selectUnidad = screen.getByLabelText('Unidad de venta')
      expect(selectUnidad).toHaveAttribute('aria-invalid', 'true')
      expect(selectUnidad).toHaveAttribute(
        'aria-describedby',
        'error-producto-unidad-venta',
      )
      const msgUnidad = screen.getByText(VALIDATION_MESSAGES.UNIDAD_REQUIRED)
      expect(msgUnidad).toHaveAttribute('id', 'error-producto-unidad-venta')
    })

    it('limpia el error y restaura aria-invalid="false" al tipear en el campo corregido', async () => {
      const user = userEvent.setup()

      render(
        <ProductoModal
          isOpen={true}
          unidades={unidadesMock}
          onGuardar={vi.fn()}
          onCerrar={vi.fn()}
        />,
      )

      const btnSubmit = screen.getByRole('button', { name: 'Crear producto' })
      await user.click(btnSubmit)

      const inputNombre = screen.getByLabelText('Nombre del producto')
      expect(inputNombre).toHaveAttribute('aria-invalid', 'true')

      await user.type(inputNombre, 'Papas Fritas')
      expect(inputNombre).toHaveAttribute('aria-invalid', 'false')
      expect(inputNombre).not.toHaveAttribute('aria-describedby')
      expect(
        screen.queryByText(VALIDATION_MESSAGES.NOMBRE_REQUIRED),
      ).not.toBeInTheDocument()
    })

    it('adapta el atributo step del input de stock según tipo de unidad y valida RN-10 en formulario interactivo', async () => {
      const user = userEvent.setup()

      render(
        <ProductoModal
          isOpen={true}
          unidades={unidadesMock}
          onGuardar={vi.fn()}
          onCerrar={vi.fn()}
        />,
      )

      const selectUnidad = screen.getByLabelText('Unidad de venta')
      const inputStock = screen.getByLabelText('Stock disponible')

      // Por defecto sin unidad seleccionada, step="0.001"
      expect(inputStock).toHaveAttribute('step', '0.001')

      // Seleccionar unidad contable (id: 2) -> step="1"
      await user.selectOptions(selectUnidad, '2')
      expect(inputStock).toHaveAttribute('step', '1')

      // Escribir stock fraccionario en unidad contable y enviar
      await user.type(screen.getByLabelText('Nombre del producto'), 'Producto Test')
      await user.type(screen.getByLabelText('Precio base ($)'), '100')
      await user.clear(inputStock)
      await user.type(inputStock, '1.5')

      const btnSubmit = screen.getByRole('button', { name: 'Crear producto' })
      await user.click(btnSubmit)

      expect(inputStock).toHaveAttribute('aria-invalid', 'true')
      expect(inputStock).toHaveAttribute(
        'aria-describedby',
        'error-producto-stock-cantidad',
      )
      expect(
        screen.getByText(VALIDATION_MESSAGES.STOCK_INTEGER_FOR_CONTABLE),
      ).toBeInTheDocument()

      // Cambiar a unidad pesable (id: 1) -> step="0.001"
      await user.selectOptions(selectUnidad, '1')
      expect(inputStock).toHaveAttribute('step', '0.001')
    })
  })

  describe('Alerta HTTP 409 y estado isSaving', () => {
    it('muestra role="alert" con mensaje de conflicto 409 preservando valores en inputs', async () => {
      const apiErrorMessage =
        'Ya existe un producto activo con ese nombre en el catálogo (conflicto 409).'

      render(
        <ProductoModal
          isOpen={true}
          productoSeleccionado={productoMock}
          unidades={unidadesMock}
          onGuardar={vi.fn()}
          onCerrar={vi.fn()}
          apiError={apiErrorMessage}
        />,
      )

      const alert = screen.getByRole('alert')
      expect(alert).toBeInTheDocument()
      expect(alert).toHaveAttribute('aria-live', 'assertive')
      expect(alert).toHaveTextContent(apiErrorMessage)

      // Conserva valores del producto
      const inputNombre = screen.getByLabelText('Nombre del producto') as HTMLInputElement
      expect(inputNombre.value).toBe('Café de Especialidad')
    })

    it('cuando isSaving={true}, muestra "Guardando..." y deshabilita todos los controles y botones', () => {
      render(
        <ProductoModal
          isOpen={true}
          unidades={unidadesMock}
          onGuardar={vi.fn()}
          onCerrar={vi.fn()}
          isSaving={true}
        />,
      )

      const btnSubmit = screen.getByRole('button', { name: 'Guardando...' })
      expect(btnSubmit).toBeInTheDocument()
      expect(btnSubmit).toBeDisabled()

      const btnCerrar = screen.getByRole('button', { name: 'Cerrar modal' })
      expect(btnCerrar).toBeDisabled()

      const btnCancelar = screen.getByRole('button', { name: 'Cancelar' })
      expect(btnCancelar).toBeDisabled()

      expect(screen.getByLabelText('Nombre del producto')).toBeDisabled()
      expect(screen.getByLabelText('Descripción (opcional)')).toBeDisabled()
      expect(screen.getByLabelText('Precio base ($)')).toBeDisabled()
      expect(screen.getByLabelText('Unidad de venta')).toBeDisabled()
      expect(screen.getByLabelText('Stock disponible')).toBeDisabled()
      expect(screen.getByLabelText('Disponible para la venta')).toBeDisabled()
    })
  })
})
