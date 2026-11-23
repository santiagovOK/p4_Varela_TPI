/**
 * Contenedor visual base para agrupar contenido de catálogo, resumen o formularios.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Tabla "Componentes compartidos — shared/ui/" (pág. 18): `Card`.
 */
import type { HTMLAttributes, ReactNode } from 'react'

export interface CardProps extends HTMLAttributes<HTMLElement> {
  title?: string
  subtitle?: string
  headerAction?: ReactNode
  footer?: ReactNode
  as?: 'div' | 'section' | 'article'
}

/** Tarjeta semántica con cabecera y pie opcionales. */
export function Card({
  title,
  subtitle,
  headerAction,
  footer,
  as = 'div',
  className = '',
  children,
  ...props
}: CardProps) {
  const Component = as
  const hasHeader = Boolean(title || subtitle || headerAction)

  return (
    <Component
      className={`bg-white border border-slate-200 rounded-xl shadow-sm ${className}`.trim()}
      {...props}
    >
      {hasHeader && (
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-5 py-4">
          <div className="space-y-0.5">
            {title && <h2 className="text-base font-semibold text-slate-900">{title}</h2>}
            {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
          </div>
          {headerAction && <div className="shrink-0">{headerAction}</div>}
        </div>
      )}

      <div className="p-5">{children}</div>

      {footer && (
        <div className="border-t border-slate-100 px-5 py-3 bg-slate-50/60 rounded-b-xl">
          {footer}
        </div>
      )}
    </Component>
  )
}
