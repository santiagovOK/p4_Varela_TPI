/**
 * Instancia compartida de TanStack Query para la caché y sincronización del estado del servidor.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Sección "Separación del estado" y tabla "Componentes compartidos — shared/api/queryClient.ts"
 *   (págs. 17–18).
 */
import { QueryClient } from '@tanstack/react-query'

/** Instancia única de `QueryClient` compartida por toda la aplicación. */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      gcTime: 1000 * 60 * 10,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})
