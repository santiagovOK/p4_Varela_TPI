/**
 * Hook TanStack Query para consultar el detalle inmutable de un pedido por ID.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Reglas `RN-04`, `RN-05`, historia `HU-TPI-03` y ruta `/mis-pedidos/:id` (págs. 5, 13–14, 18–20).
 */
import { useQuery } from '@tanstack/react-query'

import { handleApiError } from '@/shared/api/handleApiError'

import { getPedidoById } from '../api/pedidosApi'
import type { PedidoRead } from '../types/pedido.types'

/** Consulta el detalle completo de un pedido cuando `id` es un entero positivo válido. */
export function usePedidoDetalle(id: number) {
  const isValidId = Number.isInteger(id) && id > 0

  return useQuery<PedidoRead, Error>({
    queryKey: ['pedidos', id] as const,
    queryFn: async () => {
      try {
        return await getPedidoById(id)
      } catch (failure) {
        throw handleApiError(failure)
      }
    },
    enabled: isValidId,
  })
}
