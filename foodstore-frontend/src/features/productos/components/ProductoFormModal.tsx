/**
 * Modal controlado con TanStack Form para alta y edición de productos (`HU-TPI-04`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "Formularios", relación 1:N `Producto -> Categoria` y validación segura de `imagen_url` (págs. 14, 18–20).
 */
import { useForm } from '@tanstack/react-form'
import { useEffect, useId } from 'react'

import type { CategoriaRead } from '@/features/categorias'
import { Button, Input, Modal } from '@/shared/ui'

import type { ProductoCreate, ProductoRead } from '../types/producto.types'
import {
  extractProductoFieldError,
  validateCategoriaId,
  validateImagenUrl,
  validatePrecioBase,
  validateProductoNombre,
  validateStock,
} from '../validation/productoValidation'

export interface ProductoFormModalProps {
  isOpen: boolean
  onClose: () => void
  producto?: ProductoRead | null
  categorias: CategoriaRead[]
  onSubmit: (data: ProductoCreate) => Promise<void>
  isPending?: boolean
  error?: string | null
}

interface ProductoFormValues {
  nombre: string
  descripcion: string
  precio_base: string
  stock: string
  disponible: boolean
  categoria_id: string
  imagen_url: string
}

function buildDefaultValues(producto: ProductoRead | null): ProductoFormValues {
  return {
    nombre: producto?.nombre ?? '',
    descripcion: producto?.descripcion ?? '',
    precio_base: producto !== null ? String(producto.precio_base) : '',
    stock: producto !== null ? String(producto.stock) : '0',
    disponible: producto?.disponible ?? true,
    categoria_id: producto !== null ? String(producto.categoria_id) : '',
    imagen_url: producto?.imagen_url ?? '',
  }
}

/** Modal de formulario para crear o editar un producto con validación de campos y selección de categoría. */
export function ProductoFormModal({
  isOpen,
  onClose,
  producto = null,
  categorias,
  onSubmit,
  isPending = false,
  error = null,
}: ProductoFormModalProps) {
  const categoriaSelectId = useId()
  const categoriaErrorId = `${categoriaSelectId}-error`
  const descripcionId = useId()
  const disponibleId = useId()
  const isEdit = Boolean(producto)

  const defaultValues: ProductoFormValues = buildDefaultValues(producto)

  const form = useForm({
    defaultValues,
    onSubmit: async ({ value }) => {
      try {
        const trimmedDescripcion = value.descripcion.trim()
        const trimmedImagenUrl = value.imagen_url.trim()
        await onSubmit({
          nombre: value.nombre.trim(),
          descripcion: trimmedDescripcion.length > 0 ? trimmedDescripcion : null,
          precio_base: Number(value.precio_base.trim()),
          stock: Number(value.stock.trim()),
          disponible: value.disponible,
          categoria_id: Number(value.categoria_id),
          imagen_url: trimmedImagenUrl.length > 0 ? trimmedImagenUrl : null,
        })
      } catch {
        // El error permanece en la mutación para mostrarlo en el modal sin perder los datos.
      }
    },
  })

  useEffect(() => {
    if (isOpen) {
      form.reset(buildDefaultValues(producto))
    }
  }, [isOpen, producto, form])

  return (
    <form.Subscribe selector={(state) => state.isSubmitting}>
      {(isSubmitting) => {
        const busy = isSubmitting || isPending

        return (
          <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={isEdit ? 'Editar producto' : 'Nuevo producto'}
            isSubmitting={busy}
            busy={busy}
          >
            <form
              noValidate
              aria-busy={busy}
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault()
                event.stopPropagation()
                void form.handleSubmit()
              }}
            >
              {error && (
                <div
                  role="alert"
                  className="rounded-lg border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm font-medium text-rose-700"
                >
                  {error}
                </div>
              )}

              <form.Field
                name="nombre"
                validators={{
                  onBlur: ({ value }) => validateProductoNombre(value),
                  onSubmit: ({ value }) => validateProductoNombre(value),
                }}
              >
                {(field) => {
                  const fieldError = extractProductoFieldError(field.state.meta.errors)
                  return (
                    <Input
                      label="Nombre"
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(event) => field.handleChange(event.target.value)}
                      error={fieldError}
                      placeholder="Ej. Hamburguesa doble"
                      disabled={busy}
                      required
                    />
                  )
                }}
              </form.Field>

              <form.Field name="descripcion">
                {(field) => (
                  <div className="space-y-1.5">
                    <label
                      htmlFor={descripcionId}
                      className="block text-sm font-medium text-slate-700"
                    >
                      Descripción (opcional)
                    </label>
                    <textarea
                      id={descripcionId}
                      name={field.name}
                      rows={2}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(event) => field.handleChange(event.target.value)}
                      disabled={busy}
                      placeholder="Ingredientes o detalle del producto"
                      className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-1 disabled:bg-slate-100 disabled:text-slate-500 disabled:cursor-not-allowed"
                    />
                  </div>
                )}
              </form.Field>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <form.Field
                  name="precio_base"
                  validators={{
                    onBlur: ({ value }) => validatePrecioBase(value),
                    onSubmit: ({ value }) => validatePrecioBase(value),
                  }}
                >
                  {(field) => {
                    const fieldError = extractProductoFieldError(field.state.meta.errors)
                    return (
                      <Input
                        label="Precio base"
                        name={field.name}
                        type="number"
                        min={0}
                        step="0.01"
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(event) => field.handleChange(event.target.value)}
                        error={fieldError}
                        placeholder="0.00"
                        disabled={busy}
                        required
                      />
                    )
                  }}
                </form.Field>

                <form.Field
                  name="stock"
                  validators={{
                    onBlur: ({ value }) => validateStock(value),
                    onSubmit: ({ value }) => validateStock(value),
                  }}
                >
                  {(field) => {
                    const fieldError = extractProductoFieldError(field.state.meta.errors)
                    return (
                      <Input
                        label="Stock"
                        name={field.name}
                        type="number"
                        min={0}
                        step={1}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(event) => field.handleChange(event.target.value)}
                        error={fieldError}
                        disabled={busy}
                        required
                      />
                    )
                  }}
                </form.Field>
              </div>

              <form.Field
                name="categoria_id"
                validators={{
                  onBlur: ({ value }) => validateCategoriaId(value),
                  onSubmit: ({ value }) => validateCategoriaId(value),
                }}
              >
                {(field) => {
                  const fieldError = extractProductoFieldError(field.state.meta.errors)
                  const hasError = Boolean(fieldError)
                  return (
                    <div className="space-y-1.5">
                      <label
                        htmlFor={categoriaSelectId}
                        className="block text-sm font-medium text-slate-700"
                      >
                        Categoría
                      </label>
                      <select
                        id={categoriaSelectId}
                        name={field.name}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(event) => field.handleChange(event.target.value)}
                        disabled={busy}
                        aria-invalid={hasError || undefined}
                        aria-describedby={hasError ? categoriaErrorId : undefined}
                        className={`w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 disabled:bg-slate-100 disabled:text-slate-500 disabled:cursor-not-allowed ${
                          hasError
                            ? 'border-rose-500 focus-visible:ring-rose-500'
                            : 'border-slate-300 focus-visible:ring-blue-600'
                        }`}
                      >
                        <option value="">Seleccioná una categoría</option>
                        {categorias.map((cat) => (
                          <option key={cat.id} value={String(cat.id)}>
                            {cat.nombre}
                          </option>
                        ))}
                      </select>
                      {hasError && (
                        <p
                          id={categoriaErrorId}
                          role="alert"
                          className="text-xs font-medium text-rose-600"
                        >
                          {fieldError}
                        </p>
                      )}
                    </div>
                  )
                }}
              </form.Field>

              <form.Field
                name="imagen_url"
                validators={{
                  onBlur: ({ value }) => validateImagenUrl(value),
                  onSubmit: ({ value }) => validateImagenUrl(value),
                }}
              >
                {(field) => {
                  const fieldError = extractProductoFieldError(field.state.meta.errors)
                  return (
                    <Input
                      label="URL de imagen (opcional)"
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(event) => field.handleChange(event.target.value)}
                      error={fieldError}
                      helperText="Permitido: https://, http:// o ruta relativa /img/."
                      placeholder="https://ejemplo.com/imagen.jpg o /img/producto.png"
                      disabled={busy}
                    />
                  )
                }}
              </form.Field>

              <form.Field name="disponible">
                {(field) => (
                  <div className="flex items-center gap-2.5 pt-1">
                    <input
                      id={disponibleId}
                      name={field.name}
                      type="checkbox"
                      checked={field.state.value}
                      onChange={(event) => field.handleChange(event.target.checked)}
                      disabled={busy}
                      className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-600"
                    />
                    <label htmlFor={disponibleId} className="text-sm font-medium text-slate-700">
                      Disponible para la venta
                    </label>
                  </div>
                )}
              </form.Field>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button type="button" variant="secondary" disabled={busy} onClick={onClose}>
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  isLoading={busy}
                  loadingText={isEdit ? 'Guardando…' : 'Creando…'}
                >
                  {isEdit ? 'Guardar cambios' : 'Crear producto'}
                </Button>
              </div>
            </form>
          </Modal>
        )
      }}
    </form.Subscribe>
  )
}
