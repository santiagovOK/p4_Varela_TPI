/**
 * Cliente HTTP de categorías para el catálogo público.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "API REST — Categorías" (pág. 12) y "Arquitectura por features — api/" (págs. 17–18).
 */
import { axiosInstance } from '@/shared/api/axiosInstance'

import type { CategoriaRead } from '../types/categoria.types'

/** Obtiene el listado completo de categorías activas (`GET /api/v1/categorias`). */
export async function getCategorias(): Promise<CategoriaRead[]> {
  const response = await axiosInstance.get<CategoriaRead[]>('/categorias')
  return response.data
}
