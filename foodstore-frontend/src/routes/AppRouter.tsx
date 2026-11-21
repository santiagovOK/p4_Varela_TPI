/**
 * Enrutador principal de la aplicación con rutas públicas, protegidas y administrativas.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "Estructura de carpetas del frontend — routes/AppRouter.tsx" (pág. 19)
 *   y tabla "Rutas y pantallas" (págs. 19–20).
 */
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { ProtectedRoute } from '@/shared/components/ProtectedRoute'
import { MainLayout } from '@/shared/layout'

interface RoutePlaceholderProps {
  title: string
  description: string
}

function RoutePlaceholder({ title, description }: RoutePlaceholderProps) {
  return (
    <section className="flex min-h-[50vh] items-center justify-center p-6">
      <div className="max-w-lg text-center space-y-2">
        <h1 className="text-2xl font-bold">{title}</h1>
        <p className="text-sm text-slate-600">{description}</p>
      </div>
    </section>
  )
}

/** Tabla declarativa de rutas de la aplicación (apta para `MemoryRouter` en tests). */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        {/* Rutas públicas */}
        <Route
          path="/"
          element={
            <RoutePlaceholder
              title="Food Store"
              description="Catálogo público pendiente de integración en E8.2."
            />
          }
        />
        <Route
          path="/carrito"
          element={
            <RoutePlaceholder
              title="Carrito"
              description="Resumen de carrito pendiente de integración en E8.3."
            />
          }
        />
        <Route
          path="/login"
          element={
            <RoutePlaceholder
              title="Iniciar sesión"
              description="Formulario de acceso pendiente de integración en E8.1."
            />
          }
        />
        <Route
          path="/register"
          element={
            <RoutePlaceholder
              title="Crear cuenta"
              description="Formulario de registro pendiente de integración en E8.1."
            />
          }
        />
        <Route
          path="/unauthorized"
          element={
            <RoutePlaceholder
              title="Acceso no autorizado"
              description="No tenés permisos para acceder a esta sección."
            />
          }
        />

        {/* Rutas protegidas para usuarios autenticados */}
        <Route element={<ProtectedRoute />}>
          <Route
            path="/checkout"
            element={
              <RoutePlaceholder
                title="Confirmar pedido"
                description="Checkout pendiente de integración en E8.3."
              />
            }
          />
          <Route
            path="/mis-pedidos"
            element={
              <RoutePlaceholder
                title="Mis pedidos"
                description="Historial de pedidos pendiente de integración en E8.4."
              />
            }
          />
          <Route
            path="/mis-pedidos/:id"
            element={
              <RoutePlaceholder
                title="Detalle de pedido"
                description="Detalle de pedido pendiente de integración en E8.4."
              />
            }
          />
        </Route>

        {/* Rutas protegidas para administradores */}
        <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
          <Route
            path="/admin/resumen"
            element={
              <RoutePlaceholder
                title="Resumen administrativo"
                description="Panel de resumen pendiente de integración en E9.1."
              />
            }
          />
          <Route
            path="/admin/categorias"
            element={
              <RoutePlaceholder
                title="Gestión de categorías"
                description="ABM de categorías pendiente de integración en E9.2."
              />
            }
          />
          <Route
            path="/admin/productos"
            element={
              <RoutePlaceholder
                title="Gestión de productos"
                description="ABM de productos pendiente de integración en E9.2."
              />
            }
          />
          <Route
            path="/admin/pedidos"
            element={
              <RoutePlaceholder
                title="Gestión de pedidos"
                description="Panel de pedidos pendiente de integración en E9.3."
              />
            }
          />
          <Route
            path="/admin/usuarios"
            element={
              <RoutePlaceholder
                title="Gestión de usuarios"
                description="Panel de usuarios pendiente de integración en E9.4."
              />
            }
          />
        </Route>
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

/** Enrutador declarativo principal de la aplicación. */
export function AppRouter() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}

export default AppRouter
