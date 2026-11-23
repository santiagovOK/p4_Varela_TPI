/**
 * Componente de estado de error con variante de alerta principal y variante no destructiva para refetch.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Tabla "Componentes compartidos — shared/components/" (pág. 18): `EstadoError`.
 */
import { Button } from '@/shared/ui'

export type EstadoErrorVariant = 'alert' | 'inline-refetch'

export interface EstadoErrorProps {
  title?: string
  message: string
  onRetry?: () => void
  retryLabel?: string
  variant?: EstadoErrorVariant
  isRefetchError?: boolean
  className?: string
}

/**
 * Muestra errores comprensibles al usuario:
 * - `'alert'` (default): bloque principal con `role="alert"`.
 * - `'inline-refetch'` (o `isRefetchError`): aviso compacto no destructivo (`role="status"`)
 *   que informa el fallo manteniendo visibles los últimos datos confirmados.
 */
export function EstadoError({
  title,
  message,
  onRetry,
  retryLabel = 'Reintentar',
  variant = 'alert',
  isRefetchError = false,
  className = '',
}: EstadoErrorProps) {
  const isNonDestructive = variant === 'inline-refetch' || isRefetchError

  if (isNonDestructive) {
    return (
      <div
        role="status"
        aria-live="polite"
        className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 ${className}`.trim()}
      >
        <div className="flex items-start gap-2.5">
          <svg
            aria-hidden="true"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="mt-0.5 h-5 w-5 shrink-0 text-amber-600"
          >
            <path
              fillRule="evenodd"
              d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495ZM10 6a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 10 6Zm0 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
              clipRule="evenodd"
            />
          </svg>
          <div>
            <p className="font-medium">
              {title ??
                'No se pudieron actualizar los datos; se conservan los últimos datos confirmados.'}
            </p>
            <p className="text-amber-800">{message}</p>
          </div>
        </div>

        {onRetry && (
          <Button variant="secondary" size="sm" onClick={onRetry}>
            {retryLabel}
          </Button>
        )}
      </div>
    )
  }

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={`rounded-xl border border-rose-200 bg-rose-50 p-5 text-rose-900 ${className}`.trim()}
    >
      <div className="flex items-start gap-3">
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="mt-0.5 h-5 w-5 shrink-0 text-rose-600"
        >
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16ZM8.28 7.22a.75.75 0 0 0-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 1 0 1.06 1.06L10 11.06l1.72 1.72a.75.75 0 1 0 1.06-1.06L11.06 10l1.72-1.72a.75.75 0 0 0-1.06-1.06L10 8.94 8.28 7.22Z"
            clipRule="evenodd"
          />
        </svg>

        <div className="flex-1 space-y-1">
          <h3 className="text-sm font-semibold">
            {title ?? 'Ocurrió un error al cargar la información'}
          </h3>
          <p className="text-sm text-rose-800">{message}</p>

          {onRetry && (
            <div className="pt-2">
              <Button variant="danger" size="sm" onClick={onRetry}>
                {retryLabel}
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
