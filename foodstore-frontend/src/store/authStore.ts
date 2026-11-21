import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { useShallow } from 'zustand/react/shallow'

import type { UserPublic, UserRole } from '@/features/auth'
import {
  axiosInstance,
  setAuthGenerationGetter,
  setUnauthorizedHandler,
} from '@/shared/api/axiosInstance'
import {
  type ApiErrorWithCause,
  getHttpErrorStatus,
  handleApiError,
  isDisabledAccountError,
} from '@/shared/api/handleApiError'
import { queryClient } from '@/shared/api/queryClient'

export const AUTH_STORAGE_KEY = 'foodstore-auth'

export interface AuthState {
  usuario: UserPublic | null
  cargando: boolean
  error: ApiErrorWithCause | null
  login: (username: string, password: string) => Promise<UserPublic>
  logout: () => Promise<void>
  checkSession: () => Promise<void>
  clearSession: () => void
  expireSession: () => void
  hasRole: (...roles: UserRole[]) => boolean
}

let authGeneration = 0
let activeCheck: Promise<void> | null = null

/** Retorna la generación de autenticación vigente para descartar respuestas obsoletas. */
export function getAuthGeneration(): number {
  return authGeneration
}

/**
 * Vincula de forma idempotente el getter de generación y el manejador de expiración
 * sobre `axiosInstance` sin mutar el store desde fuera mediante `setState`.
 */
export function registerAuthInterceptorHandlers(): void {
  setAuthGenerationGetter(() => authGeneration)
  setUnauthorizedHandler(() => {
    useAuthStore.getState().clearSession()
  })
}

export const useAuthStore = create<AuthState>()(
  persist<AuthState, [], [], Pick<AuthState, 'usuario'>>(
    (set, get) => ({
      usuario: null,
      cargando: true,
      error: null,

      async login(username, password) {
        const generation = ++authGeneration
        activeCheck = null
        set({ cargando: true, error: null })

        try {
          const form = new URLSearchParams({ username, password })
          await axiosInstance.post('/auth/token', form, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          })

          const { data: user } = await axiosInstance.get<UserPublic>('/auth/me')
          if (generation === authGeneration) {
            queryClient.clear()
            set({ usuario: user, cargando: false, error: null })
          }
          return user
        } catch (failure) {
          const normalized = handleApiError(failure)
          if (generation === authGeneration) {
            set({ error: normalized, cargando: false })
          }
          throw normalized
        }
      },

      checkSession() {
        if (activeCheck !== null) {
          return activeCheck
        }

        const generation = authGeneration
        set({ cargando: true, error: null })

        let pending!: Promise<void>
        pending = (async () => {
          try {
            const { data: user } = await axiosInstance.get<UserPublic>('/auth/me')
            if (generation === authGeneration) {
              const prev = get().usuario
              if (
                !prev ||
                prev.id !== user.id ||
                prev.username !== user.username ||
                prev.role !== user.role
              ) {
                queryClient.clear()
              }
              set({ usuario: user, cargando: false, error: null })
            }
          } catch (failure) {
            if (generation === authGeneration) {
              const normalized = handleApiError(failure)
              const status = getHttpErrorStatus(normalized)
              const disabled = isDisabledAccountError(normalized)

              if (status === 401 || disabled) {
                queryClient.clear()
                set({
                  usuario: null,
                  cargando: false,
                  error: disabled ? normalized : null,
                })
              } else {
                set({ cargando: false, error: normalized })
              }
            }
          } finally {
            if (activeCheck === pending) {
              activeCheck = null
            }
          }
        })()

        activeCheck = pending
        return pending
      },

      async logout() {
        const generation = ++authGeneration
        activeCheck = null
        set({ cargando: true, error: null })

        try {
          await axiosInstance.post('/auth/logout')
        } catch (failure) {
          const normalized = handleApiError(failure)
          if (generation === authGeneration) {
            set({ error: normalized })
          }
          throw normalized
        } finally {
          if (generation === authGeneration) {
            queryClient.clear()
            set({ usuario: null, cargando: false })
          }
        }
      },

      clearSession() {
        ++authGeneration
        activeCheck = null
        queryClient.clear()
        set({ usuario: null, cargando: false, error: null })
      },

      expireSession() {
        get().clearSession()
      },

      hasRole(...roles) {
        const current = get().usuario
        return current !== null && roles.includes(current.role)
      },
    }),
    {
      name: AUTH_STORAGE_KEY,
      partialize: (state) => ({ usuario: state.usuario }),
    },
  ),
)

/** Selector shallow para consumir el estado de sesión en componentes UI. */
export function useAuthSession() {
  return useAuthStore(
    useShallow((state) => ({
      usuario: state.usuario,
      cargando: state.cargando,
      error: state.error,
    })),
  )
}

registerAuthInterceptorHandlers()
