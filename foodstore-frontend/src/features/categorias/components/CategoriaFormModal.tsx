/**
 * Modal controlado con TanStack Form para alta y edición de categorías (`HU-TPI-04`).
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Sección "Formularios" y "Componentes compartidos — Modal" (págs. 18–20).
 */
import { useForm } from '@tanstack/react-form'
import { useEffect, useId } from 'react'

import { Button, Input, Modal } from '@/shared/ui'

import type { CategoriaCreate, CategoriaRead } from '../types/categoria.types'
import {
  extractFieldError,
  validateCategoriaDescripcion,
  validateCategoriaNombre,
} from '../validation/categoriaValidation'

export interface CategoriaFormModalProps {
  isOpen: boolean
  onClose: () => void
  categoria?: CategoriaRead | null
  onSubmit: (data: CategoriaCreate) => Promise<void>
  isPending?: boolean
  error?: string | null
}

interface CategoriaFormValues {
  nombre: string
  descripcion: string
}

/** Modal de formulario para crear o editar una categoría preservando datos ante errores de API. */
export function CategoriaFormModal({
  isOpen,
  onClose,
  categoria = null,
  onSubmit,
  isPending = false,
  error = null,
}: CategoriaFormModalProps) {
  const descripcionId = useId()
  const descripcionErrorId = `${descripcionId}-error`
  const isEdit = Boolean(categoria)

  const defaultValues: CategoriaFormValues = {
    nombre: categoria?.nombre ?? '',
    descripcion: categoria?.descripcion ?? '',
  }

  const form = useForm({
    defaultValues,
    onSubmit: async ({ value }) => {
      try {
        const trimmedDescripcion = value.descripcion.trim()
        await onSubmit({
          nombre: value.nombre.trim(),
          descripcion: trimmedDescripcion.length > 0 ? trimmedDescripcion : null,
        })
      } catch {
        // El error permanece en la mutación para mostrarlo en el modal sin perder los datos.
      }
    },
  })

  useEffect(() => {
    if (isOpen) {
      form.reset({
        nombre: categoria?.nombre ?? '',
        descripcion: categoria?.descripcion ?? '',
      })
    }
  }, [isOpen, categoria, form])

  return (
    <form.Subscribe selector={(state) => state.isSubmitting}>
      {(isSubmitting) => {
        const busy = isSubmitting || isPending

        return (
          <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={isEdit ? 'Editar categoría' : 'Nueva categoría'}
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
                  onBlur: ({ value }) => validateCategoriaNombre(value),
                  onSubmit: ({ value }) => validateCategoriaNombre(value),
                }}
              >
                {(field) => {
                  const fieldError = extractFieldError(field.state.meta.errors)
                  return (
                    <Input
                      label="Nombre"
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(event) => field.handleChange(event.target.value)}
                      error={fieldError}
                      placeholder="Ej. Hamburguesas"
                      disabled={busy}
                      required
                    />
                  )
                }}
              </form.Field>

              <form.Field
                name="descripcion"
                validators={{
                  onBlur: ({ value }) => validateCategoriaDescripcion(value),
                  onSubmit: ({ value }) => validateCategoriaDescripcion(value),
                }}
              >
                {(field) => {
                  const fieldError = extractFieldError(field.state.meta.errors)
                  const hasError = Boolean(fieldError)
                  return (
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
                        rows={3}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(event) => field.handleChange(event.target.value)}
                        disabled={busy}
                        aria-invalid={hasError || undefined}
                        aria-describedby={hasError ? descripcionErrorId : undefined}
                        placeholder="Descripción breve de la categoría"
                        className={`w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 disabled:bg-slate-100 disabled:text-slate-500 disabled:cursor-not-allowed ${
                          hasError
                            ? 'border-rose-500 focus-visible:ring-rose-500'
                            : 'border-slate-300 focus-visible:ring-blue-600'
                        }`}
                      />
                      {hasError && (
                        <p
                          id={descripcionErrorId}
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
                  {isEdit ? 'Guardar cambios' : 'Crear categoría'}
                </Button>
              </div>
            </form>
          </Modal>
        )
      }}
    </form.Subscribe>
  )
}
