/**
 * Cliente HTTP de usuarios para administración (`HU-TPI-06`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "API REST — Usuarios (Admin)" (pág. 12) y "Arquitectura por features — api/" (págs. 17–18).
 */
import { axiosInstance } from '@/shared/api/axiosInstance'

import type { UserPublic } from '../types/usuario.types'

/** Obtiene el listado completo de usuarios para administración (`GET /api/v1/admin/usuarios`). */
export async function getUsuariosAdmin(): Promise<UserPublic[]> {
  const response = await axiosInstance.get<UserPublic[]>('/admin/usuarios')
  return response.data
}

/** Activa una cuenta de usuario desactivada (`POST /api/v1/admin/usuarios/{id}/activar`). */
export async function activarUsuario(id: number): Promise<UserPublic> {
  const response = await axiosInstance.post<UserPublic>(`/admin/usuarios/${id}/activar`)
  return response.data
}

/** Desactiva una cuenta de usuario activa (`POST /api/v1/admin/usuarios/{id}/desactivar`). */
export async function desactivarUsuario(id: number): Promise<UserPublic> {
  const response = await axiosInstance.post<UserPublic>(`/admin/usuarios/${id}/desactivar`)
  return response.data
}
