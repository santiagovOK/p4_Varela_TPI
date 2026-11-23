/**
 * Cliente HTTP de productos para catálogo público y administración ABM.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Sección "API REST — Productos" (págs. 12–14) y "Arquitectura por features — api/" (págs. 17–18).
 */
import { axiosInstance } from '@/shared/api/axiosInstance'

import type {
  ProductoCreate,
  ProductoRead,
  ProductosFilterParams,
  ProductosPaginados,
  ProductoStockUpdate,
  ProductoUpdate,
} from '../types/producto.types'

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

/** Obtiene el detalle de un producto activo por ID (`GET /api/v1/productos/{id}`). */
export async function getProducto(id: number): Promise<ProductoRead> {
  const response = await axiosInstance.get<ProductoRead>(`/productos/${id}`)
  return response.data
}

/** Crea un nuevo producto (`POST /api/v1/productos`). */
export async function createProducto(data: ProductoCreate): Promise<ProductoRead> {
  const response = await axiosInstance.post<ProductoRead>('/productos', data)
  return response.data
}

/** Actualiza un producto existente (`PUT /api/v1/productos/{id}`). */
export async function updateProducto(id: number, data: ProductoUpdate): Promise<ProductoRead> {
  const response = await axiosInstance.put<ProductoRead>(`/productos/${id}`, data)
  return response.data
}

/** Actualiza el stock y disponibilidad de un producto (`PATCH /api/v1/productos/{id}/stock`). */
export async function updateStockProducto(
  id: number,
  data: ProductoStockUpdate,
): Promise<ProductoRead> {
  const response = await axiosInstance.patch<ProductoRead>(`/productos/${id}/stock`, data)
  return response.data
}

/** Realiza la baja lógica de un producto (`DELETE /api/v1/productos/{id}`). */
export async function deleteProducto(id: number): Promise<void> {
  await axiosInstance.delete(`/productos/${id}`)
}
