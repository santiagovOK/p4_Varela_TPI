/**
 * Contratos de tipos para autenticación alineados con los schemas del backend (`auth`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "Arquitectura por features — Tipos" (pág. 17) y tablas "Auth y usuarios" / "Schemas"
 *   (págs. 11–12 y 14).
 */
import type { UserCreate, UserPublic, UserRole } from '@/features/usuarios'

export type { UserPublic, UserRole }

/** Credenciales para inicio de sesión (`POST /auth/token`). */
export interface LoginCredentials {
  username: string
  password: string
}

/** Carga útil para registro público (`POST /auth/register`). */
export type RegisterPayload = UserCreate

/** Respuesta de autenticación exitosa (`POST /auth/token` / `POST /auth/logout`). */
export interface LoginResponse {
  message: string
}
