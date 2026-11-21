/**
 * Barrel público de la feature `productos`.
 * Trazabilidad (`docs/consignas_tpi.md`): sección "Arquitectura por features" (págs. 17–18).
 */
export { getProductos } from './api/productosApi'
export {
  ProductoCard,
  formatPrecio,
  isValidImageUrl,
  type ProductoCardProps,
} from './components/ProductoCard'
export {
  CATALOGO_DEFAULT_LIMIT,
  PRODUCTOS_QUERY_KEY,
  useProductos,
} from './hooks/useProductos'
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
