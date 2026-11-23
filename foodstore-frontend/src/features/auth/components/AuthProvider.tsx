/**
 * Proveedor raíz encargado de verificar la sesión vigente al montar la aplicación.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Sección "Separación del estado" (pág. 17) y "Estructura de carpetas del frontend — App.tsx"
 *   (pág. 19): único `useEffect` que invoca `checkSession` al montar la aplicación.
 */
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
