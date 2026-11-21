/**
 * Barra de navegación principal con enlaces públicos, estado del carrito, sesión y accesos admin.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Tabla "Componentes compartidos — shared/layout/" (pág. 18): `Navbar` con nombre, rol,
 *   «Cerrar sesión» y acceso al panel solo para `admin`.
 * - Tabla "Rutas y pantallas" (págs. 19–20) y "Estado, datos y sesión — Logout" (pág. 20).
 */
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { useAuth } from '@/features/auth'
import { Button } from '@/shared/ui'
import { useCartCount } from '@/store/cartStore'

const ADMIN_LINKS = [
  { to: '/admin/resumen', label: 'Resumen' },
  { to: '/admin/categorias', label: 'Categorías' },
  { to: '/admin/productos', label: 'Productos' },
  { to: '/admin/pedidos', label: 'Pedidos' },
  { to: '/admin/usuarios', label: 'Usuarios' },
] as const

const NAV_LINK_CLASSES =
  'rounded-md px-2.5 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600'

/** Barra de navegación superior sensible al estado de autenticación, rol y carrito. */
export function Navbar() {
  const { usuario, logout } = useAuth()
  const cartCount = useCartCount()
  const navigate = useNavigate()
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  async function handleLogout() {
    setIsLoggingOut(true)
    try {
      await logout()
    } catch {
      // authStore.logout() limpia usuario y queryClient en try/finally
    } finally {
      setIsLoggingOut(false)
      navigate('/login', { replace: true })
    }
  }

  return (
    <header className="border-b border-slate-200 bg-white">
      <nav
        aria-label="Navegación principal"
        className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8"
      >
        <div className="flex flex-wrap items-center gap-2 sm:gap-4">
          <Link
            to="/"
            className="rounded-md px-1.5 py-1 text-lg font-bold tracking-tight text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
          >
            Food Store
          </Link>

          <div className="flex flex-wrap items-center gap-1">
            <Link to="/" className={NAV_LINK_CLASSES}>
              Catálogo
            </Link>

            <Link
              to="/carrito"
              aria-label={`Carrito (${cartCount} productos)`}
              className={`${NAV_LINK_CLASSES} inline-flex items-center gap-1.5`}
            >
              <span>Carrito</span>
              <span
                data-testid="cart-badge"
                className="inline-flex min-w-5 items-center justify-center rounded-full bg-blue-600 px-1.5 py-0.5 text-xs font-semibold text-white"
              >
                {cartCount}
              </span>
            </Link>

            {usuario !== null && (
              <Link to="/mis-pedidos" className={NAV_LINK_CLASSES}>
                Mis pedidos
              </Link>
            )}

            {usuario?.role === 'admin' &&
              ADMIN_LINKS.map((item) => (
                <Link key={item.to} to={item.to} className={NAV_LINK_CLASSES}>
                  {item.label}
                </Link>
              ))}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {usuario ? (
            <>
              <div className="flex items-center gap-2 text-sm">
                <span className="font-medium text-slate-900">
                  {usuario.full_name || usuario.username}
                </span>
                <span
                  className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${
                    usuario.role === 'admin'
                      ? 'border-blue-300 bg-blue-50 text-blue-800'
                      : 'border-slate-300 bg-slate-100 text-slate-700'
                  }`}
                >
                  {usuario.role === 'admin' ? 'Admin' : 'Cliente'}
                </span>
              </div>

              <Button
                variant="secondary"
                size="sm"
                isLoading={isLoggingOut}
                onClick={handleLogout}
              >
                Cerrar sesión
              </Button>
            </>
          ) : (
            <div className="flex items-center gap-2">
              <Link to="/login" className={NAV_LINK_CLASSES}>
                Iniciar sesión
              </Link>
              <Link
                to="/register"
                className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
              >
                Registrarse
              </Link>
            </div>
          )}
        </div>
      </nav>
    </header>
  )
}
