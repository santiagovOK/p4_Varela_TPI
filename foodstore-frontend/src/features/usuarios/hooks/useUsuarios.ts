/**
 * Hook administrativo de usuarios con TanStack Query (`useQuery` + `useMutation`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Historia `HU-TPI-06`, ruta `/admin/usuarios` y sección "Estado, datos y sesión" (págs. 17–20).
 */
import { useMutation, useQuery } from '@tanstack/react-query'

import { handleApiError, type ApiErrorWithCause } from '@/shared/api/handleApiError'
import { queryClient } from '@/shared/api/queryClient'

import { activarUsuario, desactivarUsuario, getUsuariosAdmin } from '../api/usuariosApi'
import type { UserPublic } from '../types/usuario.types'

export const ADMIN_USUARIOS_QUERY_KEY = ['usuarios', 'admin'] as const

/**
 * Consulta la lista administrativa de usuarios y provee mutaciones para activar/desactivar
 * cuentas invalidando `['usuarios', 'admin']` tras cada operación exitosa.
 */
export function useUsuarios() {
  const usuariosQuery = useQuery<UserPublic[], ApiErrorWithCause>(
    {
      queryKey: ADMIN_USUARIOS_QUERY_KEY,
      queryFn: async () => {
        try {
          return await getUsuariosAdmin()
        } catch (failure) {
          throw handleApiError(failure)
        }
      },
    },
    queryClient,
  )

  const activarMutation = useMutation<UserPublic, ApiErrorWithCause, number>(
    {
      mutationFn: async (id) => {
        try {
          return await activarUsuario(id)
        } catch (failure) {
          throw handleApiError(failure)
        }
      },
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ADMIN_USUARIOS_QUERY_KEY })
      },
    },
    queryClient,
  )

  const desactivarMutation = useMutation<UserPublic, ApiErrorWithCause, number>(
    {
      mutationFn: async (id) => {
        try {
          return await desactivarUsuario(id)
        } catch (failure) {
          throw handleApiError(failure)
        }
      },
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ADMIN_USUARIOS_QUERY_KEY })
      },
    },
    queryClient,
  )

  return {
    usuariosQuery,
    activarMutation,
    desactivarMutation,
  }
}
