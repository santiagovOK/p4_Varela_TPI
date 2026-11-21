/**
 * Constantes de mensajes y validadores puros con `.trim()` para formularios de autenticación.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "Schemas" (`UserCreate`, págs. 14 y 19): `username` (1–50), `full_name` (1–150),
 *   `email` válido y `password` (8–72 caracteres y <= 72 bytes UTF-8 para bcrypt).
 */

export const AUTH_VALIDATION_MESSAGES = {
  USERNAME_REQUIRED: 'El nombre de usuario es obligatorio.',
  USERNAME_LENGTH: 'El nombre de usuario debe tener entre 1 y 50 caracteres.',
  FULL_NAME_REQUIRED: 'El nombre completo es obligatorio.',
  FULL_NAME_LENGTH: 'El nombre completo debe tener entre 1 y 150 caracteres.',
  EMAIL_REQUIRED: 'El correo electrónico es obligatorio.',
  EMAIL_INVALID: 'Ingresá un correo electrónico válido.',
  PASSWORD_REQUIRED: 'La contraseña es obligatoria.',
  PASSWORD_MIN_LENGTH: 'La contraseña debe tener entre 8 y 72 caracteres.',
  PASSWORD_MAX_UTF8_BYTES: 'La contraseña no puede superar los 72 bytes en UTF-8.',
} as const

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const utf8Encoder = new TextEncoder()

/** Valida `username` tras `.trim()` (1–50 caracteres). */
export function validateUsername(value: string): string | undefined {
  const trimmed = value.trim()
  if (trimmed.length === 0) {
    return AUTH_VALIDATION_MESSAGES.USERNAME_REQUIRED
  }
  if (trimmed.length > 50) {
    return AUTH_VALIDATION_MESSAGES.USERNAME_LENGTH
  }
  return undefined
}

/** Valida `password` tras `.trim()` (8–72 caracteres y máximo 72 bytes UTF-8). */
export function validatePassword(value: string): string | undefined {
  const trimmed = value.trim()
  if (trimmed.length === 0) {
    return AUTH_VALIDATION_MESSAGES.PASSWORD_REQUIRED
  }
  if (trimmed.length < 8 || trimmed.length > 72) {
    return AUTH_VALIDATION_MESSAGES.PASSWORD_MIN_LENGTH
  }
  if (utf8Encoder.encode(trimmed).length > 72) {
    return AUTH_VALIDATION_MESSAGES.PASSWORD_MAX_UTF8_BYTES
  }
  return undefined
}

/** Valida `full_name` tras `.trim()` (1–150 caracteres). */
export function validateFullName(value: string): string | undefined {
  const trimmed = value.trim()
  if (trimmed.length === 0) {
    return AUTH_VALIDATION_MESSAGES.FULL_NAME_REQUIRED
  }
  if (trimmed.length > 150) {
    return AUTH_VALIDATION_MESSAGES.FULL_NAME_LENGTH
  }
  return undefined
}

/** Valida formato básico de `email` tras `.trim()`. */
export function validateEmail(value: string): string | undefined {
  const trimmed = value.trim()
  if (trimmed.length === 0) {
    return AUTH_VALIDATION_MESSAGES.EMAIL_REQUIRED
  }
  if (!EMAIL_PATTERN.test(trimmed)) {
    return AUTH_VALIDATION_MESSAGES.EMAIL_INVALID
  }
  return undefined
}

/** Normaliza y deduplica el primer mensaje de error de `field.state.meta.errors` en TanStack Form. */
export function extractFieldError(errors: readonly unknown[]): string | null {
  const seen = new Set<string>()
  for (const item of errors) {
    if (typeof item === 'string') {
      const trimmed = item.trim()
      if (trimmed.length > 0 && !seen.has(trimmed)) {
        seen.add(trimmed)
        return trimmed
      }
    }
  }
  return null
}
