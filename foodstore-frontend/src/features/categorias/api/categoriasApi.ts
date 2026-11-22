/**
 * Cliente HTTP de categorías para catálogo público y administración ABM.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "API REST — Categorías" (pág. 12) y "Arquitectura por features — api/" (págs. 17–18).
 */
import { axiosInstance } from '@/shared/api/axiosInstance'

import type { CategoriaCreate, CategoriaRead, CategoriaUpdate } from '../types/categoria.types'

/** Obtiene el listado completo de categorías activas (`GET /api/v1/categorias`). */
export async function getCategorias(): Promise<CategoriaRead[]> {
  const response = await axiosInstance.get<CategoriaRead[]>('/categorias')
  return response.data
}

/** Obtiene una categoría activa por ID (`GET /api/v1/categorias/{id}`). */
export async function getCategoria(id: number): Promise<CategoriaRead> {
  const response = await axiosInstance.get<CategoriaRead>(`/categorias/${id}`)
  return response.data
}

/** Crea una nueva categoría (`POST /api/v1/categorias`). */
export async function createCategoria(data: CategoriaCreate): Promise<CategoriaRead> {
  const response = await axiosInstance.post<CategoriaRead>('/categorias', data)
  return response.data
}

/** Actualiza una categoría existente (`PUT /api/v1/categorias/{id}`). */
export async function updateCategoria(id: number, data: CategoriaUpdate): Promise<CategoriaRead> {
  const response = await axiosInstance.put<CategoriaRead>(`/categorias/${id}`, data)
  return response.data
}

/** Realiza la baja lógica de una categoría (`DELETE /api/v1/categorias/{id}`). */
export async function deleteCategoria(id: number): Promise<void> {
  await axiosInstance.delete(`/categorias/${id}`)
}
