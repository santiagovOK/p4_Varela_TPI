/**
 * Modal controlado con TanStack Form para actualizar stock y disponibilidad (`PATCH /productos/{id}/stock`).
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Historia `HU-TPI-04` y endpoint `PATCH /api/v1/productos/{id}/stock` (págs. 13–14).
 */
import { useForm } from '@tanstack/react-form'
import { useEffect, useId } from 'react'

import { Button, Input, Modal } from '@/shared/ui'

import type { ProductoRead, ProductoStockUpdate } from '../types/producto.types'
import { extractProductoFieldError, validateStock } from '../validation/productoValidation'

export interface StockModalProps {
  isOpen: boolean
  onClose: () => void
  producto: ProductoRead | null
  onSubmit: (data: ProductoStockUpdate) => Promise<void>
  isPending?: boolean
  error?: string | null
}

interface StockFormValues {
  stock: string
  disponible: boolean
}

/** Modal de edición rápida de stock y disponibilidad de un producto. */
export function StockModal({
  isOpen,
  onClose,
  producto,
  onSubmit,
  isPending = false,
  error = null,
}: StockModalProps) {
  const disponibleId = useId()

  const defaultValues: StockFormValues = {
    stock: producto !== null ? String(producto.stock) : '0',
    disponible: producto?.disponible ?? true,
  }

  const form = useForm({
    defaultValues,
    onSubmit: async ({ value }) => {
      try {
        await onSubmit({
          stock: Number(value.stock.trim()),
          disponible: value.disponible,
        })
      } catch {
        // El error permanece en la mutación para mostrarlo en el modal sin perder los datos.
      }
    },
  })

  useEffect(() => {
    if (isOpen && producto) {
      form.reset({
        stock: String(producto.stock),
        disponible: producto.disponible,
      })
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
            title={producto ? `Stock de ${producto.nombre}` : 'Actualizar stock'}
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
                      label="Stock disponible"
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

              <form.Field name="disponible">
                {(field) => (
                  <div className="flex items-center gap-2.5">
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
                      Disponible en catálogo
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
                  loadingText="Actualizando…"
                >
                  Guardar stock
                </Button>
              </div>
            </form>
          </Modal>
        )
      }}
    </form.Subscribe>
  )
}
