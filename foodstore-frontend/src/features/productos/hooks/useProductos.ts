/**
 * Hook TanStack Query para listar productos paginados del catálogo público.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "Arquitectura por features — hooks/" y "Estado, datos y sesión" (págs. 17–18).
 */
import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { getProductos } from '../api/productosApi'
import type { ProductosFilterParams, ProductosPaginados } from '../types/producto.types'

export const PRODUCTOS_QUERY_KEY = 'productos' as const
export const CATALOGO_DEFAULT_LIMIT = 8

/**
 * Consulta productos paginados conservando los datos previos (`keepPreviousData`)
 * durante cambios de página/filtro o ante errores de refetch.
 */
export function useProductos(params: ProductosFilterParams = {}) {
  const normalizedSearch = params.search?.trim() ?? ''
  const normalizedCategoriaId =
    params.categoria_id !== undefined && params.categoria_id > 0
      ? params.categoria_id
      : undefined
  const skip = params.skip ?? 0
  const limit = params.limit ?? CATALOGO_DEFAULT_LIMIT
  const disponible = params.disponible ?? true

  return useQuery<ProductosPaginados, Error>({
    queryKey: [
      PRODUCTOS_QUERY_KEY,
      {
        search: normalizedSearch,
        categoria_id: normalizedCategoriaId,
        skip,
        limit,
        disponible,
      },
    ] as const,
    queryFn: () =>
      getProductos({
        search: normalizedSearch || undefined,
        categoria_id: normalizedCategoriaId,
        skip,
        limit,
        disponible,
      }),
    placeholderData: keepPreviousData,
  })
}
