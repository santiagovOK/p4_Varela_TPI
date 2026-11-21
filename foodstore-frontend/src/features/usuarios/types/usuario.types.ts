/**
 * Contratos de tipos para usuarios alineados con los schemas del backend (`usuarios`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "Arquitectura por features — Tipos" (pág. 17) y tabla "Schemas" (pág. 14).
 */
/** Roles de usuario válidos en la aplicación. */
export type UserRole = 'user' | 'admin'

/** DTO público de usuario retornado por el backend (7 campos). */
export interface UserPublic {
  id: number
  username: string
  full_name: string
  email: string
  role: UserRole
  disabled: boolean
  created_at: string
}

/** DTO de entrada para registro de un nuevo usuario. */
export interface UserCreate {
  username: string
  full_name: string
  email: string
  password: string
}
