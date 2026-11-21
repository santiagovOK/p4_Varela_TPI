/**
 * Hook TanStack Query para consultar las categorías del catálogo.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "Arquitectura por features — hooks/" y "Estado, datos y sesión" (págs. 17–18).
 */
import { useQuery } from '@tanstack/react-query'

import { getCategorias } from '../api/categoriasApi'
import type { CategoriaRead } from '../types/categoria.types'

export const CATEGORIAS_QUERY_KEY = ['categorias'] as const

/** Consulta las categorías activas cacheadas bajo `['categorias']`. */
export function useCategorias() {
  return useQuery<CategoriaRead[], Error>({
    queryKey: CATEGORIAS_QUERY_KEY,
    queryFn: getCategorias,
  })
}
