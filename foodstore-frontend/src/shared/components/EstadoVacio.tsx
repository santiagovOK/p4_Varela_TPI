/**
 * Estado vacío accesible con descripción y acción contextual opcional.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Tabla "Componentes compartidos — shared/components/" (págs. 18–19): `EstadoVacio`.
 */
import type { ReactNode } from 'react'

import { Button } from '@/shared/ui'

export interface EstadoVacioProps {
  title: string
  description?: string
  actionLabel?: string
  onAction?: () => void
  action?: ReactNode
  className?: string
}

/** Presenta una colección sin resultados diferenciándola explícitamente de carga y error. */
export function EstadoVacio({
  title,
  description,
  actionLabel,
  onAction,
  action,
  className = '',
}: EstadoVacioProps) {
  const renderedAction =
    action ??
    (actionLabel && onAction ? (
      <Button variant="secondary" size="sm" onClick={onAction}>
        {actionLabel}
      </Button>
    ) : null)

  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center ${className}`.trim()}
    >
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className="mb-3 h-10 w-10 text-slate-400"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M20.25 7.5l-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5m8.25 3v6.75m0 0-3-3m3 3 3-3M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z"
        />
      </svg>

      <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      {description && (
        <p className="mt-1 max-w-md text-sm text-slate-600">{description}</p>
      )}

      {renderedAction && <div className="mt-4">{renderedAction}</div>}
    </div>
  )
}
