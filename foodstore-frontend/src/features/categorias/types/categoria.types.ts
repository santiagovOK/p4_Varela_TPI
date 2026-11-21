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
