/**
 * Contratos de tipos para productos alineados con los schemas del backend (`productos`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "Arquitectura por features — Tipos" (pág. 17) y tabla "Schemas" (pág. 14).
 */
import type { CategoriaRead } from '@/features/categorias'

/** DTO de salida pública para un producto con su categoría asociada. */
export interface ProductoRead {
  id: number
  nombre: string
  descripcion: string | null
  precio_base: number
  imagen_url: string | null
  stock: number
  disponible: boolean
  categoria_id: number
  activo: boolean
  categoria: CategoriaRead
}

export type Producto = ProductoRead

/** DTO de entrada para crear un producto. */
export interface ProductoCreate {
  nombre: string
  descripcion?: string | null
  precio_base: number
  imagen_url?: string | null
  stock?: number
  disponible?: boolean
  categoria_id: number
}

/** DTO de entrada para actualización parcial de un producto. */
export interface ProductoUpdate {
  nombre?: string
  descripcion?: string | null
  precio_base?: number
  imagen_url?: string | null
  stock?: number
  disponible?: boolean
  categoria_id?: number
}

/** DTO de entrada para actualizar stock y disponibilidad (`PATCH /productos/{id}/stock`). */
export interface ProductoStockUpdate {
  stock: number
  disponible: boolean
}

/** DTO de salida paginada para listados de productos. */
export interface ProductosPaginados {
  total: number
  items: ProductoRead[]
}

/** Parámetros de consulta aceptados por `GET /productos`. */
export interface ProductosFilterParams {
  skip?: number
  limit?: number
  search?: string
  categoria_id?: number
  disponible?: boolean
}
