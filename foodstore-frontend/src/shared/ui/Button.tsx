/**
 * Primitiva visual de botón reutilizable con variantes, tamaños y estado de carga accesible.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Tabla "Componentes compartidos — shared/ui/" (pág. 18): `Button`.
 */
import type { ButtonHTMLAttributes } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'
export type ButtonSize = 'sm' | 'md' | 'lg'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  isLoading?: boolean
  loadingText?: string
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    'bg-blue-600 text-white hover:bg-blue-700 focus-visible:ring-blue-600 border border-transparent',
  secondary:
    'bg-white text-slate-700 hover:bg-slate-50 focus-visible:ring-slate-500 border border-slate-300',
  danger:
    'bg-rose-600 text-white hover:bg-rose-700 focus-visible:ring-rose-600 border border-transparent',
  ghost:
    'bg-transparent text-slate-700 hover:bg-slate-100 focus-visible:ring-slate-500 border border-transparent',
}

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-2.5 text-base',
}

/** Botón accesible con soporte de teclado, foco visible y bloqueo en `isLoading`. */
export function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  loadingText,
  type = 'button',
  disabled,
  className = '',
  children,
  ...props
}: ButtonProps) {
  const isDisabled = Boolean(disabled || isLoading)

  return (
    <button
      type={type}
      disabled={isDisabled}
      aria-busy={isLoading || undefined}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${className}`.trim()}
      {...props}
    >
      {isLoading && (
        <span
          aria-hidden="true"
          className="h-3.5 w-3.5 rounded-full border-2 border-current border-t-transparent animate-spin motion-reduce:animate-none"
        />
      )}
      <span>{isLoading && loadingText ? loadingText : children}</span>
    </button>
  )
}
