/**
 * Hook TanStack Query para consultar el resumen administrativo de pedidos.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Historia `HU-TPI-05`, endpoint `GET /pedidos/resumen` y ruta `/admin/resumen` (págs. 14, 18–20).
 */
import { useQuery } from '@tanstack/react-query'

import { handleApiError } from '@/shared/api/handleApiError'

import { getResumenPedidos } from '../api/pedidosApi'
import type { ResumenPedidos } from '../types/pedido.types'
import { PEDIDOS_RESUMEN_QUERY_KEY } from './useCrearPedido'

/** Consulta los indicadores agregados de pedidos para el panel administrativo. */
export function useResumenPedidos() {
  return useQuery<ResumenPedidos, Error>({
    queryKey: PEDIDOS_RESUMEN_QUERY_KEY,
    queryFn: async () => {
      try {
        return await getResumenPedidos()
      } catch (failure) {
        throw handleApiError(failure)
      }
    },
  })
}
