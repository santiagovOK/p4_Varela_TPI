/**
 * Constantes de mensajes y validadores puros con `.trim()` para formularios de productos y stock.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "Schemas — ProductoCreate / ProductoUpdate / ProductoStockUpdate" (pág. 14) y `HU-TPI-04`.
 */

export const PRODUCTO_VALIDATION_MESSAGES = {
  NOMBRE_REQUIRED: 'El nombre del producto es obligatorio.',
  PRECIO_BASE_INVALID: 'El precio base debe ser un número válido mayor o igual a 0.',
  STOCK_INVALID: 'El stock debe ser un número entero mayor o igual a 0.',
  CATEGORIA_REQUIRED: 'Seleccioná una categoría válida.',
  IMAGEN_URL_INVALID:
    'La URL de imagen debe comenzar con https://, http:// o /img/ (sin rutas relativas con .. ni esquemas inseguros).',
} as const

/** Valida `nombre` tras `.trim()` (no vacío). */
export function validateProductoNombre(value: string): string | undefined {
  if (value.trim().length === 0) {
    return PRODUCTO_VALIDATION_MESSAGES.NOMBRE_REQUIRED
  }
  return undefined
}

/** Valida `precio_base` (`>= 0` finito). */
export function validatePrecioBase(value: number | string): string | undefined {
  const numeric = typeof value === 'string' ? Number(value.trim()) : value
  if (typeof value === 'string' && value.trim().length === 0) {
    return PRODUCTO_VALIDATION_MESSAGES.PRECIO_BASE_INVALID
  }
  if (!Number.isFinite(numeric) || numeric < 0) {
    return PRODUCTO_VALIDATION_MESSAGES.PRECIO_BASE_INVALID
  }
  return undefined
}

/** Valida `stock` (`>= 0` entero). */
export function validateStock(value: number | string): string | undefined {
  if (typeof value === 'string' && value.trim().length === 0) {
    return PRODUCTO_VALIDATION_MESSAGES.STOCK_INVALID
  }
  const numeric = typeof value === 'string' ? Number(value.trim()) : value
  if (!Number.isInteger(numeric) || numeric < 0) {
    return PRODUCTO_VALIDATION_MESSAGES.STOCK_INVALID
  }
  return undefined
}

/** Valida `categoria_id` (`>= 1` entero). */
export function validateCategoriaId(value: number | string): string | undefined {
  if (typeof value === 'string' && value.trim().length === 0) {
    return PRODUCTO_VALIDATION_MESSAGES.CATEGORIA_REQUIRED
  }
  const numeric = typeof value === 'string' ? Number(value.trim()) : value
  if (!Number.isInteger(numeric) || numeric < 1) {
    return PRODUCTO_VALIDATION_MESSAGES.CATEGORIA_REQUIRED
  }
  return undefined
}

/**
 * Valida `imagen_url` (opcional; vacío tras `.trim()` es válido).
 * Si tiene contenido, debe comenzar con `https://`, `http://` o `/img/`,
 * bloqueando `javascript:`, `data:`, `vbscript:`, `//`, etc., y sin `..`.
 */
export function validateImagenUrl(value: string | null | undefined): string | undefined {
  if (value === null || value === undefined) {
    return undefined
  }
  const trimmed = value.trim()
  if (trimmed.length === 0) {
    return undefined
  }

  const lower = trimmed.toLowerCase()
  if (
    trimmed.startsWith('//') ||
    lower.startsWith('javascript:') ||
    lower.startsWith('data:') ||
    lower.startsWith('vbscript:') ||
    trimmed.includes('..')
  ) {
    return PRODUCTO_VALIDATION_MESSAGES.IMAGEN_URL_INVALID
  }

  if (trimmed.startsWith('https://') || trimmed.startsWith('http://')) {
    return undefined
  }

  if (trimmed.startsWith('/img/')) {
    return undefined
  }

  return PRODUCTO_VALIDATION_MESSAGES.IMAGEN_URL_INVALID
}

/** Normaliza y deduplica el primer mensaje de error de `field.state.meta.errors` en TanStack Form. */
export function extractProductoFieldError(errors: readonly unknown[]): string | null {
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
