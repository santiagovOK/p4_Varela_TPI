/**
 * Enrutador principal de la aplicación con rutas públicas, protegidas y administrativas.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "Estructura de carpetas del frontend — routes/AppRouter.tsx" (pág. 19)
 *   y tabla "Rutas y pantallas" (págs. 19–20).
 */
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { LoginPage, RegisterPage, UnauthorizedPage } from '@/features/auth'
import { AdminCategoriasPage } from '@/features/categorias'
import {
  AdminPedidosPage,
  AdminResumenPage,
  CarritoPage,
  CheckoutPage,
  MisPedidosPage,
  PedidoDetallePage,
} from '@/features/pedidos'
import { AdminProductosPage, CatalogoPage } from '@/features/productos'
import { AdminUsuariosPage } from '@/features/usuarios'
import { ProtectedRoute } from '@/shared/components/ProtectedRoute'
import { MainLayout } from '@/shared/layout'

/** Tabla declarativa de rutas de la aplicación (apta para `MemoryRouter` en tests). */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        {/* Rutas públicas */}
        <Route path="/" element={<CatalogoPage />} />
        <Route path="/carrito" element={<CarritoPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/unauthorized" element={<UnauthorizedPage />} />

        {/* Rutas protegidas para usuarios autenticados */}
        <Route element={<ProtectedRoute />}>
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/mis-pedidos" element={<MisPedidosPage />} />
          <Route path="/mis-pedidos/:id" element={<PedidoDetallePage />} />
        </Route>

        {/* Rutas protegidas para administradores */}
        <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
          <Route path="/admin/resumen" element={<AdminResumenPage />} />
          <Route path="/admin/categorias" element={<AdminCategoriasPage />} />
          <Route path="/admin/productos" element={<AdminProductosPage />} />
          <Route path="/admin/pedidos" element={<AdminPedidosPage />} />
          <Route path="/admin/usuarios" element={<AdminUsuariosPage />} />
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
