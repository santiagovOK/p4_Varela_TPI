import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'

import { setupInterceptors } from '@/shared/api/axiosInstance'
import { queryClient } from '@/shared/api/queryClient'
import { registerAuthInterceptorHandlers } from '@/store/authStore'
import App from './App'
import './index.css'

setupInterceptors()
registerAuthInterceptorHandlers()

const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('No se encontró el elemento raíz #root en index.html')
}

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
