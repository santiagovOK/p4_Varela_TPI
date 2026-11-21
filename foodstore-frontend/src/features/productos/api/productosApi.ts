/**
 * Cliente HTTP de productos para el catálogo público.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "API REST — Productos" (págs. 12–14) y "Arquitectura por features — api/" (págs. 17–18).
 */
import { axiosInstance } from '@/shared/api/axiosInstance'

import type { ProductosFilterParams, ProductosPaginados } from '../types/producto.types'

/** Obtiene el listado paginado de productos (`GET /api/v1/productos`). */
export async function getProductos(
  params: ProductosFilterParams = {},
): Promise<ProductosPaginados> {
  const normalizedSearch = params.search?.trim()
  const queryParams: ProductosFilterParams = {
    skip: params.skip ?? 0,
    limit: params.limit ?? 8,
  }

  if (normalizedSearch) {
    queryParams.search = normalizedSearch
  }
  if (params.categoria_id !== undefined && params.categoria_id > 0) {
    queryParams.categoria_id = params.categoria_id
  }
  if (params.disponible !== undefined) {
    queryParams.disponible = params.disponible
  }

  const response = await axiosInstance.get<ProductosPaginados>('/productos', {
    params: queryParams,
  })
  return response.data
}
