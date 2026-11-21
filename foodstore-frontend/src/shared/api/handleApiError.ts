/**
 * Normalización de errores HTTP de FastAPI hacia mensajes legibles para la interfaz.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "API REST — Errores" (`HTTPException` con `detail` string o lista `422`, págs. 10–11).
 * - Tabla "Componentes compartidos — shared/api/handleApiError.ts" (pág. 18).
 */
import axios from 'axios'

/** Error normalizado que conserva el error original en `cause` y el código HTTP en `status`. */
export type ApiErrorWithCause = Error & {
  cause?: unknown
  status?: number
}

function extractDetailMessage(detail: unknown): string | undefined {
  if (typeof detail === 'string') {
    const trimmed = detail.trim()
    return trimmed.length > 0 ? trimmed : undefined
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'object' && item !== null && 'msg' in item) {
          const msg = (item as { msg?: unknown }).msg
          return typeof msg === 'string' ? msg.trim() : ''
        }
        return ''
      })
      .filter((msg) => msg.length > 0)

    return messages.length > 0 ? messages.join('; ') : undefined
  }

  return undefined
}

/**
 * Normaliza cualquier error HTTP o de red en una instancia de `Error` legible,
 * preservando el `AxiosError` original en `error.cause`.
 */
export function handleApiError(error: unknown, fallbackMessage?: string): ApiErrorWithCause {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    const payload = error.response?.data as { detail?: unknown } | undefined
    const detail = extractDetailMessage(payload?.detail)
    const defaultHttpMsg =
      status !== undefined
        ? `Error de API (HTTP ${status})`
        : error.message || 'Error de conexión con la API'

    const normalized: ApiErrorWithCause = new Error(detail ?? fallbackMessage ?? defaultHttpMsg)
    normalized.cause = error
    if (status !== undefined) {
      normalized.status = status
    }
    return normalized
  }

  if (error instanceof Error) {
    return error as ApiErrorWithCause
  }

  const normalized: ApiErrorWithCause = new Error(
    fallbackMessage ?? 'Error inesperado en la solicitud',
  )
  normalized.cause = error
  return normalized
}

/** Extrae el código de estado HTTP recorriendo la cadena de `cause` sin ciclos. */
export function getHttpErrorStatus(error: unknown): number | undefined {
  const visited = new Set<unknown>()
  let current: unknown = error

  while (current !== null && current !== undefined && !visited.has(current)) {
    visited.add(current)

    if (typeof current === 'object') {
      const candidate = current as { status?: unknown; cause?: unknown }
      if (typeof candidate.status === 'number') {
        return candidate.status
      }
      if (axios.isAxiosError(current) && current.response?.status !== undefined) {
        return current.response.status
      }
      current = candidate.cause
    } else {
      break
    }
  }

  return undefined
}

/** Indica si el error corresponde a una cuenta de usuario desactivada (HTTP 400). */
export function isDisabledAccountError(error: unknown): boolean {
  return (
    getHttpErrorStatus(error) === 400 &&
    error instanceof Error &&
    /cuenta de usuario desactivada/i.test(error.message)
  )
}
