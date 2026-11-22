/**
 * Barrel público de la feature `categorias`.
 * Trazabilidad (`docs/consignas_tpi.md`): sección "Arquitectura por features" (págs. 17–18).
 */
export {
  createCategoria,
  deleteCategoria,
  getCategoria,
  getCategorias,
  updateCategoria,
} from './api/categoriasApi'
export { CategoriaFormModal, type CategoriaFormModalProps } from './components/CategoriaFormModal'
export {
  useAdminCategorias,
  type UpdateCategoriaVariables,
} from './hooks/useAdminCategorias'
export { CATEGORIAS_QUERY_KEY, useCategorias } from './hooks/useCategorias'
export { AdminCategoriasPage } from './pages/AdminCategoriasPage'
export type {
  Categoria,
  CategoriaCreate,
  CategoriaRead,
  CategoriaUpdate,
} from './types/categoria.types'
export {
  CATEGORIA_VALIDATION_MESSAGES,
  extractFieldError,
  validateCategoriaDescripcion,
  validateCategoriaNombre,
} from './validation/categoriaValidation'
