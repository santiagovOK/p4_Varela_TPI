/**
 * Componente raíz de composición entre verificación de sesión (`AuthProvider`) y rutas (`AppRouter`).
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Sección "Estructura de carpetas del frontend — App.tsx" (pág. 19).
 */
import { AuthProvider } from '@/features/auth'
import { AppRouter } from '@/routes/AppRouter'

export function App() {
  return (
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  )
}

export default App
