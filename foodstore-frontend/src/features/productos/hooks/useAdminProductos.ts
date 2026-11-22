/**
 * Hook TanStack Query para la administración ABM de productos, stock e invalidación cruzada.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Historia `HU-TPI-04` y sección "Estado, datos y sesión" (págs. 14, 17–19).
 */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { type ApiErrorWithCause, handleApiError } from '@/shared/api/handleApiError'

import {
  createProducto,
  deleteProducto,
  getProductos,
  updateProducto,
  updateStockProducto,
} from '../api/productosApi'
import type {
  ProductoCreate,
  ProductoRead,
  ProductosPaginados,
  ProductoStockUpdate,
  ProductoUpdate,
} from '../types/producto.types'
import { PRODUCTOS_QUERY_KEY } from './useProductos'

export const PRODUCTOS_ADMIN_QUERY_KEY = [PRODUCTOS_QUERY_KEY, 'admin'] as const
export const ADMIN_PRODUCTOS_LIMIT = 100

export interface UpdateProductoVariables {
  id: number
  data: ProductoUpdate
}

export interface UpdateStockProductoVariables {
  id: number
  data: ProductoStockUpdate
}

/** Hook administrativo para listar, crear, editar, actualizar stock y dar de baja productos. */
export function useAdminProductos() {
  const queryClient = useQueryClient()

  const productosQuery = useQuery<ProductosPaginados, Error>({
    queryKey: PRODUCTOS_ADMIN_QUERY_KEY,
    queryFn: () => getProductos({ limit: ADMIN_PRODUCTOS_LIMIT, skip: 0 }),
    placeholderData: keepPreviousData,
  })

  const invalidateCatalogo = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: [PRODUCTOS_QUERY_KEY] }),
      queryClient.invalidateQueries({ queryKey: ['categorias'] }),
    ])
  }

  const createMutation = useMutation<ProductoRead, ApiErrorWithCause, ProductoCreate>({
    mutationFn: async (data) => {
      try {
        return await createProducto(data)
      } catch (error) {
        throw handleApiError(error, 'No se pudo crear el producto.')
      }
    },
    onSuccess: async () => {
      await invalidateCatalogo()
    },
  })

  const updateMutation = useMutation<ProductoRead, ApiErrorWithCause, UpdateProductoVariables>({
    mutationFn: async ({ id, data }) => {
      try {
        return await updateProducto(id, data)
      } catch (error) {
        throw handleApiError(error, 'No se pudo actualizar el producto.')
      }
    },
    onSuccess: async () => {
      await invalidateCatalogo()
    },
  })

  const updateStockMutation = useMutation<
    ProductoRead,
    ApiErrorWithCause,
    UpdateStockProductoVariables
  >({
    mutationFn: async ({ id, data }) => {
      try {
        return await updateStockProducto(id, data)
      } catch (error) {
        throw handleApiError(error, 'No se pudo actualizar el stock del producto.')
      }
    },
    onSuccess: async () => {
      await invalidateCatalogo()
    },
  })

  const deleteMutation = useMutation<void, ApiErrorWithCause, number>({
    mutationFn: async (id) => {
      try {
        await deleteProducto(id)
      } catch (error) {
        throw handleApiError(error, 'No se pudo eliminar el producto.')
      }
    },
    onSuccess: async (_data, id) => {
      queryClient.removeQueries({ queryKey: ['productos', id] })
      await invalidateCatalogo()
    },
  })

  return {
    productosQuery,
    createMutation,
    updateMutation,
    updateStockMutation,
    deleteMutation,
  }
}
