import { Navigate, Outlet, useLocation } from 'react-router-dom'

import type { UserRole } from '@/features/auth'
import { useAuthStore } from '@/store/authStore'

export interface ProtectedRouteProps {
  allowedRoles?: UserRole[]
}

/**
 * Guardia declarativo de rutas protegidas por sesión y rol mediante `<Outlet />`.
 * Evalúa en orden estricto: `cargando` -> `!usuario` -> `allowedRoles` -> `<Outlet />`.
 */
export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const cargando = useAuthStore((state) => state.cargando)
  const usuario = useAuthStore((state) => state.usuario)
  const location = useLocation()

  if (cargando) {
    return (
      <div
        role="status"
        aria-live="polite"
        aria-busy="true"
        className="min-h-screen bg-slate-50 text-slate-700 flex items-center justify-center p-6"
      >
        <span>Verificando sesión…</span>
      </div>
    )
  }

  if (!usuario) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  if (allowedRoles && allowedRoles.length > 0 && !allowedRoles.includes(usuario.role)) {
    return <Navigate to="/unauthorized" replace />
  }

  return <Outlet />
}

export default ProtectedRoute
