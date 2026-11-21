/**
 * Barrel público de la feature `categorias`.
 * Trazabilidad (`docs/consignas_tpi.md`): sección "Arquitectura por features" (págs. 17–18).
 */
export { getCategorias } from './api/categoriasApi'
export { CATEGORIAS_QUERY_KEY, useCategorias } from './hooks/useCategorias'
export type {
  Categoria,
  CategoriaCreate,
  CategoriaRead,
  CategoriaUpdate,
} from './types/categoria.types'
