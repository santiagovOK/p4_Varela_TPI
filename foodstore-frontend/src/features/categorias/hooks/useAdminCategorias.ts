/**
 * Hook TanStack Query para la administración ABM de categorías con invalidación cruzada y `removeQueries`.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Historia `HU-TPI-04` y sección "Estado, datos y sesión" (págs. 14, 17–19).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { type ApiErrorWithCause, handleApiError } from '@/shared/api/handleApiError'

import {
  createCategoria,
  deleteCategoria,
  getCategorias,
  updateCategoria,
} from '../api/categoriasApi'
import type { CategoriaCreate, CategoriaRead, CategoriaUpdate } from '../types/categoria.types'
import { CATEGORIAS_QUERY_KEY } from './useCategorias'

export interface UpdateCategoriaVariables {
  id: number
  data: CategoriaUpdate
}

/** Hook administrativo para listar, crear, editar y dar de baja categorías. */
export function useAdminCategorias() {
  const queryClient = useQueryClient()

  const categoriasQuery = useQuery<CategoriaRead[], Error>({
    queryKey: CATEGORIAS_QUERY_KEY,
    queryFn: getCategorias,
  })

  const invalidateCatalogo = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: CATEGORIAS_QUERY_KEY }),
      queryClient.invalidateQueries({ queryKey: ['productos'] }),
    ])
  }

  const createMutation = useMutation<CategoriaRead, ApiErrorWithCause, CategoriaCreate>({
    mutationFn: async (data) => {
      try {
        return await createCategoria(data)
      } catch (error) {
        throw handleApiError(error, 'No se pudo crear la categoría.')
      }
    },
    onSuccess: async () => {
      await invalidateCatalogo()
    },
  })

  const updateMutation = useMutation<CategoriaRead, ApiErrorWithCause, UpdateCategoriaVariables>({
    mutationFn: async ({ id, data }) => {
      try {
        return await updateCategoria(id, data)
      } catch (error) {
        throw handleApiError(error, 'No se pudo actualizar la categoría.')
      }
    },
    onSuccess: async () => {
      await invalidateCatalogo()
    },
  })

  const deleteMutation = useMutation<void, ApiErrorWithCause, number>({
    mutationFn: async (id) => {
      try {
        await deleteCategoria(id)
      } catch (error) {
        throw handleApiError(error, 'No se pudo eliminar la categoría.')
      }
    },
    onSuccess: async (_data, id) => {
      queryClient.removeQueries({ queryKey: ['categorias', id] })
      await invalidateCatalogo()
    },
  })

  return {
    categoriasQuery,
    createMutation,
    updateMutation,
    deleteMutation,
  }
}
