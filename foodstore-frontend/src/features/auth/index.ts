/**
 * Barrel público de la feature `auth`.
 * Trazabilidad (`docs/consignas_tpi.pdf`): sección "Arquitectura por features" (págs. 17–18).
 */
export { authApi } from './api/authApi'
export { AuthProvider, type AuthProviderProps } from './components/AuthProvider'
export { useAuth } from './hooks/useAuth'
export { LoginPage } from './pages/LoginPage'
export { RegisterPage } from './pages/RegisterPage'
export { UnauthorizedPage } from './pages/UnauthorizedPage'
export {
  AUTH_VALIDATION_MESSAGES,
  extractFieldError,
  validateEmail,
  validateFullName,
  validatePassword,
  validateUsername,
} from './validation/authValidation'
export type {
  LoginCredentials,
  LoginResponse,
  LogoutResponse,
  RegisterPayload,
  UserPublic,
  UserRole,
} from './types/auth.types'
