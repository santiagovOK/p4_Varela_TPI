/** Estados válidos de la máquina de estados de pedidos (RN-02). */
export type EstadoPedido = 'PENDIENTE' | 'EN_PREPARACION' | 'ENTREGADO' | 'CANCELADO'

/** Formas de pago aceptadas al crear un pedido (RN-06). */
export type FormaPago = 'EFECTIVO' | 'TRANSFERENCIA'

/** Línea de producto al crear un pedido. */
export interface ItemPedidoCreate {
  producto_id: number
  cantidad: number
}

/** DTO de entrada para crear un pedido (`POST /pedidos`). */
export interface PedidoCreate {
  items: ItemPedidoCreate[]
  forma_pago: FormaPago
  direccion_entrega: string
  notas?: string | null
}

/** Línea inmutable (snapshot) de un pedido (RN-05). */
export interface DetallePedidoRead {
  producto_id: number
  nombre_producto: string
  precio_unitario: number
  cantidad: number
  subtotal: number
}

/** DTO de salida pública para un pedido con sus líneas de detalle. */
export interface PedidoRead {
  id: number
  usuario_id: number
  estado: EstadoPedido
  forma_pago: FormaPago
  direccion_entrega: string
  notas: string | null
  total: number
  created_at: string
  updated_at: string
  items: DetallePedidoRead[]
}

export type Pedido = PedidoRead

/** DTO de salida paginada para listados de pedidos. */
export interface PedidosPaginados {
  total: number
  items: PedidoRead[]
}

/** DTO de entrada para transición administrativa de estado (`PATCH /pedidos/{id}/estado`). */
export interface CambioEstado {
  estado: EstadoPedido
}

/** DTO de salida para indicadores administrativos de pedidos (`GET /pedidos/resumen`). */
export interface ResumenPedidos {
  pendientes: number
  en_preparacion: number
  entregados: number
  cancelados: number
  pedidos_hoy: number
  ingresos_entregados: number
}
