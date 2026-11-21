/**
 * Estructura de diseño principal que envuelve las rutas con la barra de navegación y `<Outlet />`.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Tabla "Componentes compartidos — shared/layout/" (pág. 18): `MainLayout`.
 */
import { Outlet } from 'react-router-dom'

import { Navbar } from './Navbar'

/** Layout general de la aplicación con cabecera `Navbar` y región `<main>`. */
export function MainLayout() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      <Navbar />
      <main
        id="main-content"
        className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6"
      >
        <Outlet />
      </main>
    </div>
  )
}
