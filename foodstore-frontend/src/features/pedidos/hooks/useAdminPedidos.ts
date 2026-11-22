/**
 * Hook administrativo para listar pedidos y ejecutar transiciones de estado (`RN-02`, `RN-03`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Historia `HU-TPI-05`, ruta `/admin/pedidos` y regla `RN-02` (págs. 5, 14, 18–20).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { handleApiError, type ApiErrorWithCause } from '@/shared/api/handleApiError'

import { cambiarEstadoPedido, getPedidos } from '../api/pedidosApi'
import type { EstadoPedido, PedidoRead, PedidosPaginados } from '../types/pedido.types'
import {
  PEDIDOS_QUERY_KEY,
  PEDIDOS_RESUMEN_QUERY_KEY,
  PRODUCTOS_ROOT_QUERY_KEY,
} from './useCrearPedido'

export const ADMIN_PEDIDOS_QUERY_KEY = ['pedidos', 'admin'] as const

export interface CambiarEstadoPedidoVariables {
  id: number
  estado: EstadoPedido
}

/**
 * Consulta los pedidos (`limit=100, skip=0`) para gestión administrativa y provee
 * la mutación `cambiarEstadoMutation` con invalidación cruzada en paralelo.
 */
export function useAdminPedidos() {
  const queryClient = useQueryClient()

  const pedidosQuery = useQuery<PedidosPaginados, ApiErrorWithCause>({
    queryKey: ADMIN_PEDIDOS_QUERY_KEY,
    queryFn: async () => {
      try {
        return await getPedidos({ limit: 100, skip: 0 })
      } catch (failure) {
        throw handleApiError(failure)
      }
    },
  })

  const cambiarEstadoMutation = useMutation<
    PedidoRead,
    ApiErrorWithCause,
    CambiarEstadoPedidoVariables
  >({
    mutationFn: async ({ id, estado }) => {
      try {
        return await cambiarEstadoPedido(id, estado)
      } catch (failure) {
        throw handleApiError(failure)
      }
    },
    onSuccess: async (_data, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: PEDIDOS_QUERY_KEY }),
        queryClient.invalidateQueries({ queryKey: [...PEDIDOS_QUERY_KEY, variables.id] }),
        queryClient.invalidateQueries({ queryKey: PEDIDOS_RESUMEN_QUERY_KEY }),
        queryClient.invalidateQueries({ queryKey: PRODUCTOS_ROOT_QUERY_KEY }),
      ])
    },
  })

  return {
    pedidosQuery,
    cambiarEstadoMutation,
  }
}
