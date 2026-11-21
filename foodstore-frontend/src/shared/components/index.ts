/**
 * Exportaciones públicas de componentes compartidos (`src/shared/components/`).
 * Trazabilidad (`docs/consignas_tpi.md`): tabla "Componentes compartidos — shared/components/" (pág. 18).
 */
export {
  EstadoError,
  type EstadoErrorProps,
  type EstadoErrorVariant,
} from './EstadoError'
export { EstadoVacio, type EstadoVacioProps } from './EstadoVacio'
export { Paginacion, type PaginacionProps } from './Paginacion'
export { ProtectedRoute, type ProtectedRouteProps } from './ProtectedRoute'
export { Skeleton, type SkeletonProps, type SkeletonVariant } from './Skeleton'
