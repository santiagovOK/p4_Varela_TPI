/**
 * Hook de mutación para crear pedidos con normalización de errores e invalidación cruzada.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Regla `RN-01` (descuento transaccional de stock) y sección "Estado, datos y sesión" (págs. 5, 13, 17, 19–20).
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { handleApiError, type ApiErrorWithCause } from '@/shared/api/handleApiError'

import { crearPedido } from '../api/pedidosApi'
import type { PedidoCreate, PedidoRead } from '../types/pedido.types'

export const PEDIDOS_QUERY_KEY = ['pedidos'] as const
export const PEDIDOS_RESUMEN_QUERY_KEY = ['pedidos', 'resumen'] as const
export const PRODUCTOS_ROOT_QUERY_KEY = ['productos'] as const

/**
 * Ejecuta `POST /pedidos` e invalida `['pedidos']`, `['pedidos', 'resumen']` y `['productos']`
 * únicamente tras una creación exitosa (`201`).
 */
export function useCrearPedido() {
  const queryClient = useQueryClient()

  return useMutation<PedidoRead, ApiErrorWithCause, PedidoCreate>({
    mutationFn: async (payload) => {
      try {
        return await crearPedido(payload)
      } catch (failure) {
        throw handleApiError(failure)
      }
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: PEDIDOS_QUERY_KEY }),
        queryClient.invalidateQueries({ queryKey: PEDIDOS_RESUMEN_QUERY_KEY }),
        queryClient.invalidateQueries({ queryKey: PRODUCTOS_ROOT_QUERY_KEY }),
      ])
    },
  })
}
