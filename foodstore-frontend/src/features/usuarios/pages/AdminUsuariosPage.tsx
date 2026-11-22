/**
 * Página administrativa `/admin/usuarios` con buscador, TanStack Query y `UsuariosTable` (`HU-TPI-06`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Ruta `/admin/usuarios`, historia `HU-TPI-06` y sección "Tablas" (págs. 18–20).
 */
import type { PaginationState } from '@tanstack/react-table'
import { useCallback, useState } from 'react'

import { useAuth } from '@/features/auth'
import { EstadoError, Skeleton } from '@/shared/components'
import { Input } from '@/shared/ui'

import { ADMIN_USUARIOS_PAGE_SIZE, UsuariosTable } from '../components/UsuariosTable'
import { useUsuarios } from '../hooks/useUsuarios'
import type { UserPublic } from '../types/usuario.types'

/** Panel administrativo de usuarios para consultar cuentas y activar/desactivar acceso. */
export function AdminUsuariosPage() {
  const { usuario: currentUser } = useAuth()
  const { usuariosQuery, activarMutation, desactivarMutation } = useUsuarios()
  const { data, isLoading, isError, isRefetchError, error, refetch } = usuariosQuery

  const [searchFilter, setSearchFilter] = useState('')
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: ADMIN_USUARIOS_PAGE_SIZE,
  })
  const [pendingUserId, setPendingUserId] = useState<number | null>(null)

  const handleSearchChange = (value: string) => {
    setSearchFilter(value)
    setPagination((prev) => ({ ...prev, pageIndex: 0 }))
  }

  const handleResetFilters = () => {
    setSearchFilter('')
    setPagination((prev) => ({ ...prev, pageIndex: 0 }))
  }

  const handleActivar = useCallback(
    async (usuario: UserPublic) => {
      desactivarMutation.reset()
      setPendingUserId(usuario.id)
      try {
        await activarMutation.mutateAsync(usuario.id)
      } catch {
        // El error normalizado permanece en `activarMutation.error` para mostrarse en `role="alert"`.
      } finally {
        setPendingUserId(null)
      }
    },
    [activarMutation, desactivarMutation],
  )

  const handleDesactivar = useCallback(
    async (usuario: UserPublic) => {
      activarMutation.reset()
      setPendingUserId(usuario.id)
      try {
        await desactivarMutation.mutateAsync(usuario.id)
      } catch {
        // El error normalizado permanece en `desactivarMutation.error` para mostrarse en `role="alert"`.
      } finally {
        setPendingUserId(null)
      }
    },
    [activarMutation, desactivarMutation],
  )

  const handleDismissError = useCallback(() => {
    activarMutation.reset()
    desactivarMutation.reset()
  }, [activarMutation, desactivarMutation])

  const isMutating = activarMutation.isPending || desactivarMutation.isPending
  const mutationError =
    activarMutation.error?.message ?? desactivarMutation.error?.message ?? null
  const hasActiveFilters = Boolean(searchFilter.trim())

  return (
    <section className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Gestión de usuarios
        </h1>
        <p className="text-sm text-slate-600">
          Consultá las cuentas registradas y activá o desactivá su acceso al sistema.
        </p>
      </header>

      <div className="max-w-md">
        <Input
          label="Buscar usuario"
          placeholder="Buscar por #ID, usuario, nombre, email o rol…"
          value={searchFilter}
          onChange={(event) => handleSearchChange(event.target.value)}
        />
      </div>

      {isLoading && !data ? (
        <Skeleton variant="row" count={6} label="Cargando usuarios…" />
      ) : isError && !data ? (
        <EstadoError
          variant="alert"
          title="No se pudieron cargar los usuarios"
          message={error?.message ?? 'Error al consultar los usuarios.'}
          onRetry={() => void refetch()}
        />
      ) : data ? (
        <div className="space-y-4">
          {(isError || isRefetchError) && (
            <EstadoError
              variant="inline-refetch"
              title="No se pudieron actualizar los usuarios; se conservan los últimos datos confirmados."
              message={error?.message ?? 'Error al actualizar los usuarios.'}
              onRetry={() => void refetch()}
            />
          )}

          <UsuariosTable
            usuarios={data}
            currentUserId={currentUser?.id ?? null}
            globalFilter={searchFilter}
            pagination={pagination}
            onPaginationChange={setPagination}
            onActivar={handleActivar}
            onDesactivar={handleDesactivar}
            isMutating={isMutating}
            pendingUserId={pendingUserId}
            mutationError={mutationError}
            onDismissError={handleDismissError}
            hasActiveFilters={hasActiveFilters}
            onResetFilters={handleResetFilters}
          />
        </div>
      ) : null}
    </section>
  )
}
