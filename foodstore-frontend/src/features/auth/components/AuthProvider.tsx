import { useEffect, type ReactNode } from 'react'

import { useAuthStore } from '@/store/authStore'

export interface AuthProviderProps {
  children: ReactNode
}

/**
 * Proveedor raíz de sesión: ejecuta la verificación inicial contra `/auth/me`
 * al montar la aplicación, deduplicada por `activeCheck` en `authStore`.
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const checkSession = useAuthStore((state) => state.checkSession)

  useEffect(() => {
    void checkSession().catch(() => undefined)
  }, [checkSession])

  return <>{children}</>
}
