/**
 * Pantalla accesible de acceso denegado (rol insuficiente) con retorno al catálogo inicial.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Tabla "Rutas y pantallas" (`/unauthorized` — «Mensaje y enlace al inicio», págs. 18 y 20).
 */
import { Link } from 'react-router-dom'

import { Card } from '@/shared/ui'

import { useAuth } from '../hooks/useAuth'

/** Vista informativa ante intento de acceso a rutas protegidas sin el rol requerido (`admin`). */
export function UnauthorizedPage() {
  const { usuario } = useAuth()

  return (
    <section
      aria-labelledby="unauthorized-heading"
      className="mx-auto flex min-h-[60vh] max-w-lg items-center justify-center py-8"
    >
      <Card className="w-full text-center">
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-rose-600">
            Error 403
          </p>
          <h1 id="unauthorized-heading" className="text-2xl font-bold text-slate-900">
            Acceso no autorizado
          </h1>
          <p className="text-sm text-slate-600">
            No tenés los permisos necesarios para acceder a esta sección administrativa.
          </p>

          {usuario && (
            <p className="text-xs text-slate-500">
              Sesión actual: <strong>{usuario.username}</strong> (rol: {usuario.role})
            </p>
          )}

          <div className="pt-3">
            <Link
              to="/"
              className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
            >
              Volver al catálogo
            </Link>
          </div>
        </div>
      </Card>
    </section>
  )
}
