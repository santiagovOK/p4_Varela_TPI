/**
 * Indicador de carga inicial accesible mediante bloques skeleton con respeto a `prefers-reduced-motion`.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Tabla "Componentes compartidos — shared/components/" (págs. 18–19): `Skeleton`.
 */
export type SkeletonVariant = 'card' | 'row' | 'text'

export interface SkeletonProps {
  count?: number
  label?: string
  variant?: SkeletonVariant
  className?: string
}

/** Estado de carga accesible (`role="status"`, `aria-busy="true"`) con elementos decorativos ocultos. */
export function Skeleton({
  count = 3,
  label = 'Cargando contenido…',
  variant = 'card',
  className = '',
}: SkeletonProps) {
  const safeCount = Math.max(1, Math.trunc(count))

  if (variant === 'text') {
    return (
      <div
        role="status"
        aria-live="polite"
        aria-busy="true"
        className={`space-y-2.5 ${className}`.trim()}
      >
        <span className="sr-only">{label}</span>
        {Array.from({ length: safeCount }).map((_, index) => (
          <div
            key={index}
            aria-hidden="true"
            className="h-4 rounded bg-slate-200 animate-pulse motion-reduce:animate-none"
          />
        ))}
      </div>
    )
  }

  if (variant === 'row') {
    return (
      <div
        role="status"
        aria-live="polite"
        aria-busy="true"
        className={`space-y-3 ${className}`.trim()}
      >
        <span className="sr-only">{label}</span>
        {Array.from({ length: safeCount }).map((_, index) => (
          <div
            key={index}
            aria-hidden="true"
            className="h-12 rounded-lg border border-slate-200 bg-slate-200/80 animate-pulse motion-reduce:animate-none"
          />
        ))}
      </div>
    )
  }

  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className={`grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 ${className}`.trim()}
    >
      <span className="sr-only">{label}</span>
      {Array.from({ length: safeCount }).map((_, index) => (
        <div
          key={index}
          aria-hidden="true"
          className="rounded-xl border border-slate-200 bg-white p-4 space-y-3"
        >
          <div className="h-36 w-full rounded-lg bg-slate-200 animate-pulse motion-reduce:animate-none" />
          <div className="h-4 w-3/4 rounded bg-slate-200 animate-pulse motion-reduce:animate-none" />
          <div className="h-4 w-1/2 rounded bg-slate-200 animate-pulse motion-reduce:animate-none" />
        </div>
      ))}
    </div>
  )
}
