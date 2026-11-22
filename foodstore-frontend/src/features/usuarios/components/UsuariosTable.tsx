/**
 * Tabla administrativa de usuarios construida con `@tanstack/react-table` (`HU-TPI-06`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Ruta `/admin/usuarios`, historia `HU-TPI-06` y sección "Tablas" (págs. 18–20).
 */
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type OnChangeFn,
  type PaginationState,
  type SortingState,
  useReactTable,
} from '@tanstack/react-table'
import { useMemo, useState } from 'react'

import { EstadoVacio } from '@/shared/components'
import { Button } from '@/shared/ui'

import type { UserPublic } from '../types/usuario.types'

const EMPTY_USUARIOS: UserPublic[] = []
export const ADMIN_USUARIOS_PAGE_SIZE = 10
const columnHelper = createColumnHelper<UserPublic>()

function mapAriaSort(sortDirection: false | 'asc' | 'desc'): 'ascending' | 'descending' | 'none' {
  if (sortDirection === 'asc') return 'ascending'
  if (sortDirection === 'desc') return 'descending'
  return 'none'
}

function getRoleLabel(role: UserPublic['role']): string {
  return role === 'admin' ? 'Administrador' : 'Usuario'
}

export interface UsuariosTableProps {
  usuarios?: UserPublic[]
  currentUserId?: number | null
  globalFilter?: string
  pagination?: PaginationState
  onPaginationChange?: OnChangeFn<PaginationState>
  onActivar: (usuario: UserPublic) => void | Promise<void>
  onDesactivar: (usuario: UserPublic) => void | Promise<void>
  isMutating?: boolean
  pendingUserId?: number | null
  mutationError?: string | null
  onDismissError?: () => void
  hasActiveFilters?: boolean
  onResetFilters?: () => void
}

/** Tabla semántica de usuarios con ordenamiento, paginación local y acciones activar/desactivar. */
export function UsuariosTable({
  usuarios,
  currentUserId = null,
  globalFilter = '',
  pagination: controlledPagination,
  onPaginationChange,
  onActivar,
  onDesactivar,
  isMutating = false,
  pendingUserId = null,
  mutationError = null,
  onDismissError,
  hasActiveFilters = false,
  onResetFilters,
}: UsuariosTableProps) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [internalPagination, setInternalPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: ADMIN_USUARIOS_PAGE_SIZE,
  })

  const pagination = controlledPagination ?? internalPagination
  const handlePaginationChange = onPaginationChange ?? setInternalPagination
  const data = usuarios ?? EMPTY_USUARIOS

  const columns = useMemo(
    () => [
      columnHelper.accessor('id', {
        header: 'ID',
        cell: (info) => <span className="font-semibold text-slate-900">#{info.getValue()}</span>,
      }),
      columnHelper.accessor('username', {
        header: 'Usuario',
        cell: (info) => <span className="font-medium text-slate-900">{info.getValue()}</span>,
      }),
      columnHelper.accessor('full_name', {
        header: 'Nombre completo',
        cell: (info) => <span className="text-slate-700">{info.getValue()}</span>,
      }),
      columnHelper.accessor('email', {
        header: 'Email',
        cell: (info) => <span className="text-slate-700">{info.getValue()}</span>,
      }),
      columnHelper.accessor('role', {
        header: 'Rol',
        cell: (info) => (
          <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
            {getRoleLabel(info.getValue())}
          </span>
        ),
      }),
      columnHelper.accessor('disabled', {
        id: 'estado',
        header: 'Estado',
        cell: (info) => {
          const isDisabled = info.getValue()
          return (
            <span
              className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                isDisabled
                  ? 'border-rose-300 bg-rose-100 text-rose-800'
                  : 'border-emerald-300 bg-emerald-100 text-emerald-800'
              }`}
            >
              {isDisabled ? 'Desactivado' : 'Activo'}
            </span>
          )
        },
      }),
      columnHelper.display({
        id: 'acciones',
        header: 'Acciones',
        enableSorting: false,
        cell: ({ row }) => {
          const usuario = row.original
          const isCurrentUser = currentUserId !== null && usuario.id === currentUserId
          const isRowPending = isMutating && pendingUserId === usuario.id

          if (usuario.disabled) {
            return (
              <Button
                type="button"
                variant="primary"
                size="sm"
                disabled={isMutating}
                isLoading={isRowPending}
                loadingText="Activando…"
                onClick={() => void onActivar(usuario)}
              >
                Activar
              </Button>
            )
          }

          if (isCurrentUser) {
            return <span className="text-xs font-medium text-slate-500">Sesión actual</span>
          }

          return (
            <Button
              type="button"
              variant="danger"
              size="sm"
              disabled={isMutating}
              isLoading={isRowPending}
              loadingText="Desactivando…"
              onClick={() => void onDesactivar(usuario)}
            >
              Desactivar
            </Button>
          )
        },
      }),
    ],
    [currentUserId, isMutating, onActivar, onDesactivar, pendingUserId],
  )

  const table = useReactTable({
    data,
    columns,
    getRowId: (row) => String(row.id),
    state: {
      sorting,
      globalFilter,
      pagination,
    },
    onSortingChange: setSorting,
    onPaginationChange: handlePaginationChange,
    globalFilterFn: (row, _columnId, filterValue) => {
      const term = String(filterValue ?? '')
        .trim()
        .toLowerCase()
      if (!term) return true
      const usuario = row.original
      return (
        String(usuario.id).includes(term) ||
        usuario.username.toLowerCase().includes(term) ||
        usuario.full_name.toLowerCase().includes(term) ||
        usuario.email.toLowerCase().includes(term) ||
        getRoleLabel(usuario.role).toLowerCase().includes(term)
      )
    },
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  })

  const rows = table.getRowModel().rows
  const filteredCount = table.getFilteredRowModel().rows.length
  const pageCount = Math.max(1, table.getPageCount())

  return (
    <div className="space-y-4">
      {mutationError && (
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-800"
        >
          <span>{mutationError}</span>
          {onDismissError && (
            <Button type="button" variant="secondary" size="sm" onClick={onDismissError}>
              Cerrar aviso
            </Button>
          )}
        </div>
      )}

      {rows.length === 0 ? (
        <EstadoVacio
          title={
            hasActiveFilters
              ? 'No se encontraron usuarios con ese criterio'
              : 'No hay usuarios registrados'
          }
          description={
            hasActiveFilters
              ? 'Probá modificando o limpiando el término de búsqueda.'
              : 'Cuando existan usuarios en el sistema aparecerán listados aquí.'
          }
          actionLabel={hasActiveFilters && onResetFilters ? 'Limpiar búsqueda' : undefined}
          onAction={hasActiveFilters ? onResetFilters : undefined}
        />
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-xs">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-600">
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => {
                      const canSort = header.column.getCanSort()
                      const sorted = header.column.getIsSorted()
                      return (
                        <th
                          key={header.id}
                          scope="col"
                          aria-sort={canSort ? mapAriaSort(sorted) : undefined}
                          className="px-4 py-3"
                        >
                          {header.isPlaceholder ? null : canSort ? (
                            <button
                              type="button"
                              onClick={header.column.getToggleSortingHandler()}
                              className="inline-flex items-center gap-1.5 rounded font-semibold text-slate-700 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                            >
                              {flexRender(header.column.columnDef.header, header.getContext())}
                              <span aria-hidden="true" className="text-slate-400">
                                {sorted === 'asc' ? '↑' : sorted === 'desc' ? '↓' : '↕'}
                              </span>
                            </button>
                          ) : (
                            flexRender(header.column.columnDef.header, header.getContext())
                          )}
                        </th>
                      )
                    })}
                  </tr>
                ))}
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {rows.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-50/75">
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3 align-middle">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <p className="text-sm text-slate-600">
              Página {pagination.pageIndex + 1} de {pageCount} ({filteredCount} usuarios)
            </p>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={!table.getCanPreviousPage()}
                onClick={() => table.previousPage()}
              >
                Anterior
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={!table.getCanNextPage()}
                onClick={() => table.nextPage()}
              >
                Siguiente
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
