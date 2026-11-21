/**
 * Hook unificado de autenticación: expone estado de sesión y mutaciones TanStack Query.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Secciones "Arquitectura por features" y "Estado, datos y sesión" (págs. 17 y 20).
 */
import { useMutation } from '@tanstack/react-query'

import { handleApiError, type ApiErrorWithCause } from '@/shared/api/handleApiError'
import { queryClient } from '@/shared/api/queryClient'
import { useAuthSession, useAuthStore } from '@/store/authStore'

import { authApi } from '../api/authApi'
import type { LoginCredentials, RegisterPayload, UserPublic } from '../types/auth.types'

/**
 * Encapsula el acceso a `authStore` y las mutaciones `login`, `register` y `logout`
 * para páginas y componentes sin acoplarlos directamente al store ni a `axiosInstance`.
 */
export function useAuth() {
  const { usuario, cargando, error } = useAuthSession()
  const storeLogin = useAuthStore((state) => state.login)
  const storeLogout = useAuthStore((state) => state.logout)
  const checkSession = useAuthStore((state) => state.checkSession)
  const clearSession = useAuthStore((state) => state.clearSession)
  const hasRole = useAuthStore((state) => state.hasRole)

  const loginMutation = useMutation<UserPublic, ApiErrorWithCause, LoginCredentials>(
    {
      mutationFn: async (credentials) =>
        storeLogin(credentials.username.trim(), credentials.password.trim()),
    },
    queryClient,
  )

  const registerMutation = useMutation<UserPublic, ApiErrorWithCause, RegisterPayload>(
    {
      mutationFn: async (payload) => {
        try {
          return await authApi.register(payload)
        } catch (failure) {
          throw handleApiError(failure)
        }
      },
    },
    queryClient,
  )

  const logoutMutation = useMutation<void, ApiErrorWithCause, void>(
    {
      mutationFn: async () => storeLogout(),
    },
    queryClient,
  )

  return {
    usuario,
    cargando,
    error,
    isAuthenticated: usuario !== null,
    hasRole,
    clearSession,
    checkSession,
    loginMutation,
    registerMutation,
    logoutMutation,
    logout: () => logoutMutation.mutateAsync(),
  }
}
