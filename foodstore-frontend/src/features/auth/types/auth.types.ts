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
