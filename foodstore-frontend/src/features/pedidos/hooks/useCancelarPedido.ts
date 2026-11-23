/**
 * Hook de mutación para cancelar un pedido `PENDIENTE` con invalidación cruzada.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Reglas `RN-03` (restitución transaccional de stock) y `RN-04` (solo propietario en `PENDIENTE`, págs. 5, 13–14, 19–20).
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { handleApiError, type ApiErrorWithCause } from '@/shared/api/handleApiError'

import { cancelarPedido } from '../api/pedidosApi'
import type { PedidoRead } from '../types/pedido.types'
import {
  PEDIDOS_QUERY_KEY,
  PEDIDOS_RESUMEN_QUERY_KEY,
  PRODUCTOS_ROOT_QUERY_KEY,
} from './useCrearPedido'

/**
 * Ejecuta `PATCH /pedidos/{id}/cancelar` e invalida `['pedidos']`, `['pedidos', id]`,
 * `['pedidos', 'resumen']` y `['productos']` tras una cancelación exitosa (`200`).
 */
export function useCancelarPedido() {
  const queryClient = useQueryClient()

  return useMutation<PedidoRead, ApiErrorWithCause, number>({
    mutationFn: async (id) => {
      try {
        return await cancelarPedido(id)
      } catch (failure) {
        throw handleApiError(failure)
      }
    },
    onSuccess: async (_data, id) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: PEDIDOS_QUERY_KEY }),
        queryClient.invalidateQueries({ queryKey: [...PEDIDOS_QUERY_KEY, id] }),
        queryClient.invalidateQueries({ queryKey: PEDIDOS_RESUMEN_QUERY_KEY }),
        queryClient.invalidateQueries({ queryKey: PRODUCTOS_ROOT_QUERY_KEY }),
      ])
    },
  })
}
