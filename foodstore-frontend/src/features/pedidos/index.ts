/**
 * Barrel público de la feature `pedidos`.
 * Trazabilidad (`docs/consignas_tpi.pdf`): sección "Arquitectura por features" (págs. 17–18).
 */
export {
  cambiarEstadoPedido,
  cancelarPedido,
  crearPedido,
  getPedidoById,
  getPedidos,
  getResumenPedidos,
  pedidosApi,
} from './api/pedidosApi'
export { ResumenCard, type ResumenCardProps, type ResumenCardTone } from './components/ResumenCard'
export {
  ADMIN_PEDIDOS_QUERY_KEY,
  useAdminPedidos,
  type CambiarEstadoPedidoVariables,
} from './hooks/useAdminPedidos'
export { useCancelarPedido } from './hooks/useCancelarPedido'
export {
  PEDIDOS_QUERY_KEY,
  PEDIDOS_RESUMEN_QUERY_KEY,
  PRODUCTOS_ROOT_QUERY_KEY,
  useCrearPedido,
} from './hooks/useCrearPedido'
export { MIS_PEDIDOS_DEFAULT_LIMIT, useMisPedidos } from './hooks/useMisPedidos'
export { usePedidoDetalle } from './hooks/usePedidoDetalle'
export { useResumenPedidos } from './hooks/useResumenPedidos'
export { AdminPedidosPage } from './pages/AdminPedidosPage'
export { AdminResumenPage } from './pages/AdminResumenPage'
export { CarritoPage } from './pages/CarritoPage'
export { CheckoutPage } from './pages/CheckoutPage'
export { MisPedidosPage } from './pages/MisPedidosPage'
export { PedidoDetallePage } from './pages/PedidoDetallePage'
export {
  CHECKOUT_VALIDATION_MESSAGES,
  DIRECCION_MAX_LENGTH,
  DIRECCION_MIN_LENGTH,
  FORMAS_PAGO_VALIDAS,
  NOTAS_MAX_LENGTH,
  extractCheckoutFieldError,
  validateDireccionEntrega,
  validateFormaPago,
  validateNotas,
  type CheckoutFormValues,
} from './validation/checkoutValidation'
export type {
  CambioEstado,
  DetallePedidoRead,
  EstadoPedido,
  FormaPago,
  ItemPedidoCreate,
  Pedido,
  PedidoCreate,
  PedidoRead,
  PedidosPaginados,
  PedidosFilterParams,
  ResumenPedidos,
} from './types/pedido.types'
