/**
 * Hook TanStack Query para consultar el historial paginado de pedidos propios.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Regla `RN-04`, historia `HU-TPI-03` y ruta `/mis-pedidos` (págs. 5, 13–14, 18–20).
 */
import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { handleApiError } from '@/shared/api/handleApiError'
import { useAuthSession } from '@/store/authStore'

import { getPedidos } from '../api/pedidosApi'
import type { PedidosFilterParams, PedidosPaginados } from '../types/pedido.types'

export const MIS_PEDIDOS_DEFAULT_LIMIT = 10

/** Consulta paginada de pedidos del usuario autenticado con filtro opcional por estado. */
export function useMisPedidos(params: PedidosFilterParams = {}) {
  const { usuario } = useAuthSession()
  const skip = params.skip ?? 0
  const limit = params.limit ?? MIS_PEDIDOS_DEFAULT_LIMIT
  const estado = params.estado

  return useQuery<PedidosPaginados, Error>({
    queryKey: ['pedidos', { skip, limit, estado }] as const,
    queryFn: async () => {
      try {
        return await getPedidos({ skip, limit, estado })
      } catch (failure) {
        throw handleApiError(failure)
      }
    },
    select: (data) => {
      if (!usuario?.id) return data
      const itemsPropios = data.items.filter((p) => p.usuario_id === usuario.id)
      return {
        total: usuario.role === 'admin' ? itemsPropios.length : data.total,
        items: itemsPropios,
      }
    },
    placeholderData: keepPreviousData,
  })
}
