/**
 * Barrel público de la feature `productos`.
 * Trazabilidad (`docs/consignas_tpi.pdf`): sección "Arquitectura por features" (págs. 17–18).
 */
export {
  createProducto,
  deleteProducto,
  getProducto,
  getProductos,
  updateProducto,
  updateStockProducto,
} from './api/productosApi'
export {
  ADD_TO_CART_FEEDBACK_MS,
  ProductoCard,
  formatPrecio,
  isValidImageUrl,
  type ProductoCardProps,
} from './components/ProductoCard'
export { ProductoFormModal, type ProductoFormModalProps } from './components/ProductoFormModal'
export { StockModal, type StockModalProps } from './components/StockModal'
export {
  ADMIN_PRODUCTOS_LIMIT,
  PRODUCTOS_ADMIN_QUERY_KEY,
  useAdminProductos,
  type UpdateProductoVariables,
  type UpdateStockProductoVariables,
} from './hooks/useAdminProductos'
export {
  CATALOGO_DEFAULT_LIMIT,
  PRODUCTOS_QUERY_KEY,
  useProductos,
} from './hooks/useProductos'
export { AdminProductosPage } from './pages/AdminProductosPage'
export { CatalogoPage } from './pages/CatalogoPage'
export type {
  Producto,
  ProductoCreate,
  ProductoRead,
  ProductosFilterParams,
  ProductosPaginados,
  ProductoStockUpdate,
  ProductoUpdate,
} from './types/producto.types'
export {
  PRODUCTO_VALIDATION_MESSAGES,
  extractProductoFieldError,
  validateCategoriaId,
  validateImagenUrl,
  validatePrecioBase,
  validateProductoNombre,
  validateStock,
} from './validation/productoValidation'
