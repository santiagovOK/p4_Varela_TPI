/**
 * Contratos de tipos para categorías alineados con los schemas del backend (`categorias`).
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Sección "Arquitectura por features — Tipos" (pág. 17) y tabla "Schemas" (pág. 14).
 */
/** DTO de salida pública para una categoría. */
export interface CategoriaRead {
  id: number
  nombre: string
  descripcion: string | null
  activo: boolean
}

export type Categoria = CategoriaRead

/** DTO de entrada para crear una categoría. */
export interface CategoriaCreate {
  nombre: string
  descripcion?: string | null
}

/** DTO de entrada para actualización parcial de una categoría. */
export interface CategoriaUpdate {
  nombre?: string
  descripcion?: string | null
}
