/**
 * Constantes de mensajes y validadores puros con `.trim()` para formularios de categorías.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "Schemas — CategoriaCreate / CategoriaUpdate" (pág. 14) y `HU-TPI-04`.
 */

export const CATEGORIA_VALIDATION_MESSAGES = {
  NOMBRE_REQUIRED: 'El nombre de la categoría es obligatorio.',
  NOMBRE_LENGTH: 'El nombre de la categoría debe tener entre 2 y 100 caracteres.',
  DESCRIPCION_MAX_LENGTH: 'La descripción no puede superar los 500 caracteres.',
} as const

/** Valida `nombre` tras `.trim()` (2 a 100 caracteres). */
export function validateCategoriaNombre(value: string): string | undefined {
  const trimmed = value.trim()
  if (trimmed.length === 0) {
    return CATEGORIA_VALIDATION_MESSAGES.NOMBRE_REQUIRED
  }
  if (trimmed.length < 2 || trimmed.length > 100) {
    return CATEGORIA_VALIDATION_MESSAGES.NOMBRE_LENGTH
  }
  return undefined
}

/** Valida `descripcion` opcional tras `.trim()`. */
export function validateCategoriaDescripcion(value: string | null | undefined): string | undefined {
  if (value === null || value === undefined) {
    return undefined
  }
  const trimmed = value.trim()
  if (trimmed.length > 500) {
    return CATEGORIA_VALIDATION_MESSAGES.DESCRIPCION_MAX_LENGTH
  }
  return undefined
}

/** Normaliza y deduplica el primer mensaje de error de `field.state.meta.errors` en TanStack Form. */
export function extractFieldError(errors: readonly unknown[]): string | null {
  for (const item of errors) {
    if (typeof item === 'string') {
      const trimmed = item.trim()
      if (trimmed.length > 0) {
        return trimmed
      }
    }
  }
  return null
}
