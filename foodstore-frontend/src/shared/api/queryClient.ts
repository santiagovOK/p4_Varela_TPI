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
