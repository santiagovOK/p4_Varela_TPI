/**
 * Campo de entrada accesible con etiqueta asociada, texto de ayuda y error por campo.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Tabla "Componentes compartidos — shared/ui/" (pág. 18): `Input`.
 */
import { useId, type InputHTMLAttributes, type Ref } from 'react'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string | null
  helperText?: string
  ref?: Ref<HTMLInputElement>
}

/** Input controlado/no controlado con vinculación `aria-invalid`, `aria-describedby` y `role="alert"`. */
export function Input({
  label,
  error,
  helperText,
  id,
  className = '',
  'aria-describedby': externalDescribedBy,
  ref,
  ...props
}: InputProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const hasError = Boolean(error && error.trim().length > 0)
  const errorId = hasError ? `${inputId}-error` : undefined
  const helperId = helperText ? `${inputId}-helper` : undefined
  const describedBy =
    [externalDescribedBy, helperId, errorId].filter(Boolean).join(' ') || undefined

  return (
    <div className="space-y-1.5">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-slate-700">
          {label}
        </label>
      )}

      <input
        id={inputId}
        ref={ref}
        aria-invalid={hasError || undefined}
        aria-describedby={describedBy}
        className={`w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 disabled:bg-slate-100 disabled:text-slate-500 disabled:cursor-not-allowed ${
          hasError
            ? 'border-rose-500 focus-visible:ring-rose-500'
            : 'border-slate-300 focus-visible:ring-blue-600'
        } ${className}`.trim()}
        {...props}
      />

      {helperText && (
        <p id={helperId} className="text-xs text-slate-500">
          {helperText}
        </p>
      )}

      {hasError && (
        <p id={errorId} role="alert" className="text-xs font-medium text-rose-600">
          {error}
        </p>
      )}
    </div>
  )
}
