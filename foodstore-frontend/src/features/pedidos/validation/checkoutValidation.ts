/**
 * Constantes de mensajes y validadores puros con `.trim()` para el formulario de checkout.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Regla `RN-06` y schema `PedidoCreate` (págs. 5, 14 y 19).
 */
import type { FormaPago } from '../types/pedido.types'

export interface CheckoutFormValues {
  direccion_entrega: string
  forma_pago: FormaPago
  notas: string
}

export const DIRECCION_MIN_LENGTH = 5
export const DIRECCION_MAX_LENGTH = 200
/**
 * Validación defensiva en frontend: docs/consignas_tpi.md no fija una longitud máxima explícita
 * para notas (campo opcional en DTO), pero se implementa para acotar el input del formulario.
 */
export const NOTAS_MAX_LENGTH = 500

export const FORMAS_PAGO_VALIDAS: readonly FormaPago[] = ['EFECTIVO', 'TRANSFERENCIA'] as const

export const CHECKOUT_VALIDATION_MESSAGES = {
  DIRECCION_REQUIRED: 'La dirección de entrega es obligatoria.',
  DIRECCION_LENGTH: 'La dirección de entrega debe tener entre 5 y 200 caracteres.',
  FORMA_PAGO_INVALID: 'Seleccioná una forma de pago válida (Efectivo o Transferencia).',
  NOTAS_MAX_LENGTH: 'Las notas no pueden superar los 500 caracteres.',
} as const

/** Valida `direccion_entrega` tras `.trim()` (obligatoria, entre 5 y 200 caracteres). */
export function validateDireccionEntrega(value: string): string | undefined {
  const trimmed = value.trim()
  if (trimmed.length === 0) {
    return CHECKOUT_VALIDATION_MESSAGES.DIRECCION_REQUIRED
  }
  if (trimmed.length < DIRECCION_MIN_LENGTH || trimmed.length > DIRECCION_MAX_LENGTH) {
    return CHECKOUT_VALIDATION_MESSAGES.DIRECCION_LENGTH
  }
  return undefined
}

/** Valida `forma_pago` tras `.trim()` (`'EFECTIVO' | 'TRANSFERENCIA'`). */
export function validateFormaPago(value: string): string | undefined {
  const trimmed = value.trim()
  if (!FORMAS_PAGO_VALIDAS.includes(trimmed as FormaPago)) {
    return CHECKOUT_VALIDATION_MESSAGES.FORMA_PAGO_INVALID
  }
  return undefined
}

/** Valida `notas` opcionales tras `.trim()` (máximo 500 caracteres). */
export function validateNotas(value: string): string | undefined {
  const trimmed = value.trim()
  if (trimmed.length > NOTAS_MAX_LENGTH) {
    return CHECKOUT_VALIDATION_MESSAGES.NOTAS_MAX_LENGTH
  }
  return undefined
}

/** Normaliza y deduplica el primer mensaje de error de `field.state.meta.errors`. */
export function extractCheckoutFieldError(errors: readonly unknown[]): string | null {
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
