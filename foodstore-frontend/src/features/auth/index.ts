/**
 * Barrel público de la feature `auth`.
 * Trazabilidad (`docs/consignas_tpi.md`): sección "Arquitectura por features" (págs. 17–18).
 */
export { AuthProvider, type AuthProviderProps } from './components/AuthProvider'
export type {
  LoginCredentials,
  LoginResponse,
  RegisterPayload,
  UserPublic,
  UserRole,
} from './types/auth.types'
