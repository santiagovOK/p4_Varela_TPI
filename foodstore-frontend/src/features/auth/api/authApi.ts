/**
 * Cliente HTTP tipado para los endpoints de autenticación (`/auth/*`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Tablas "Auth y usuarios" y "Rutas y pantallas" (págs. 11–12 y 17–18).
 */
import { axiosInstance } from '@/shared/api/axiosInstance'

import type {
  LoginCredentials,
  LoginResponse,
  LogoutResponse,
  RegisterPayload,
  UserPublic,
} from '../types/auth.types'

/** Inicia sesión enviando credenciales OAuth2 (`x-www-form-urlencoded`) a `POST /auth/token`. */
export async function login(credentials: LoginCredentials): Promise<LoginResponse> {
  const form = new URLSearchParams({
    username: credentials.username.trim(),
    password: credentials.password.trim(),
  })
  const { data } = await axiosInstance.post<LoginResponse>('/auth/token', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data
}

/** Registra un nuevo usuario cliente mediante `POST /auth/register`. */
export async function register(payload: RegisterPayload): Promise<UserPublic> {
  const normalizedPayload: RegisterPayload = {
    username: payload.username.trim(),
    full_name: payload.full_name.trim(),
    email: payload.email.trim(),
    password: payload.password.trim(),
  }
  const { data } = await axiosInstance.post<UserPublic>('/auth/register', normalizedPayload)
  return data
}

/** Cierra la sesión vigente invocando `POST /auth/logout`. */
export async function logout(): Promise<LogoutResponse> {
  const { data } = await axiosInstance.post<LogoutResponse>('/auth/logout')
  return data
}

/** Obtiene el perfil del usuario autenticado desde `GET /auth/me`. */
export async function getMe(): Promise<UserPublic> {
  const { data } = await axiosInstance.get<UserPublic>('/auth/me')
  return data
}

export const authApi = {
  login,
  register,
  logout,
  getMe,
}
