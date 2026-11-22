/**
 * Cliente HTTP tipado para los endpoints de pedidos (`/pedidos/*`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Reglas `RN-03`, `RN-04`, `RN-05` y tablas "Pedidos" / "Rutas y pantallas" (págs. 5, 13–14, 17–20).
 */
import { axiosInstance } from '@/shared/api/axiosInstance'

import type {
  EstadoPedido,
  PedidoCreate,
  PedidoRead,
  PedidosFilterParams,
  PedidosPaginados,
  ResumenPedidos,
} from '../types/pedido.types'

/** Crea un nuevo pedido transaccional en el backend (`POST /pedidos`). */
export async function crearPedido(payload: PedidoCreate): Promise<PedidoRead> {
  const { data } = await axiosInstance.post<PedidoRead>('/pedidos', payload)
  return data
}

/** Obtiene el listado paginado de pedidos con filtro opcional por estado (`GET /pedidos`). */
export async function getPedidos(
  params: PedidosFilterParams = {},
): Promise<PedidosPaginados> {
  const queryParams: Record<string, string | number> = {}
  if (params.skip !== undefined) {
    queryParams.skip = params.skip
  }
  if (params.limit !== undefined) {
    queryParams.limit = params.limit
  }
  if (params.estado !== undefined) {
    queryParams.estado = params.estado
  }

  const { data } = await axiosInstance.get<PedidosPaginados>('/pedidos', {
    params: queryParams,
  })
  return data
}

/** Obtiene el detalle inmutable de un pedido por identificador (`GET /pedidos/{id}`). */
export async function getPedidoById(id: number): Promise<PedidoRead> {
  const { data } = await axiosInstance.get<PedidoRead>(`/pedidos/${id}`)
  return data
}

/** Cancela un pedido propio en estado `PENDIENTE` restituyendo stock (`PATCH /pedidos/{id}/cancelar`). */
export async function cancelarPedido(id: number): Promise<PedidoRead> {
  const { data } = await axiosInstance.patch<PedidoRead>(`/pedidos/${id}/cancelar`)
  return data
}

/** Obtiene los indicadores administrativos agregados de pedidos (`GET /pedidos/resumen`). */
export async function getResumenPedidos(): Promise<ResumenPedidos> {
  const { data } = await axiosInstance.get<ResumenPedidos>('/pedidos/resumen')
  return data
}

/** Transiciona el estado de un pedido como administrador según `RN-02` (`PATCH /pedidos/{id}/estado`). */
export async function cambiarEstadoPedido(
  id: number,
  estado: EstadoPedido,
): Promise<PedidoRead> {
  const { data } = await axiosInstance.patch<PedidoRead>(`/pedidos/${id}/estado`, {
    estado,
  })
  return data
}

export const pedidosApi = {
  crearPedido,
  getPedidos,
  getPedidoById,
  cancelarPedido,
  getResumenPedidos,
  cambiarEstadoPedido,
}
