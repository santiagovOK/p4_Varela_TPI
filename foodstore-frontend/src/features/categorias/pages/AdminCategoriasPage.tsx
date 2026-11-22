/**
 * Página administrativa `/admin/categorias` con TanStack Table y modales de alta/edición/baja (`HU-TPI-04`).
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Ruta `/admin/categorias`, sección "Tablas" (`@tanstack/react-table`) y "Estado, datos y sesión" (págs. 18–20).
 */
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from '@tanstack/react-table'
import { useMemo, useState } from 'react'

import { EstadoError, EstadoVacio, Skeleton } from '@/shared/components'
import { Button, Input, Modal } from '@/shared/ui'

import { CategoriaFormModal } from '../components/CategoriaFormModal'
import { useAdminCategorias } from '../hooks/useAdminCategorias'
import type { CategoriaCreate, CategoriaRead } from '../types/categoria.types'

const EMPTY_CATEGORIAS: CategoriaRead[] = []
const columnHelper = createColumnHelper<CategoriaRead>()

function mapAriaSort(sortDirection: false | 'asc' | 'desc'): 'ascending' | 'descending' | 'none' {
  if (sortDirection === 'asc') return 'ascending'
  if (sortDirection === 'desc') return 'descending'
  return 'none'
}

/** Panel administrativo de categorías con ordenamiento, filtrado y ABM modal. */
export function AdminCategoriasPage() {
  const { categoriasQuery, createMutation, updateMutation, deleteMutation } = useAdminCategorias()
  const { data, isLoading, isError, isRefetchError, error, refetch } = categoriasQuery

  const [sorting, setSorting] = useState<SortingState>([])
  const [globalFilter, setGlobalFilter] = useState('')
  const [formModalOpen, setFormModalOpen] = useState(false)
  const [editingCategoria, setEditingCategoria] = useState<CategoriaRead | null>(null)
  const [deletingCategoria, setDeletingCategoria] = useState<CategoriaRead | null>(null)

  const handleOpenCreate = () => {
    createMutation.reset()
    updateMutation.reset()
    setEditingCategoria(null)
    setFormModalOpen(true)
  }

  const handleOpenEdit = (categoria: CategoriaRead) => {
    createMutation.reset()
    updateMutation.reset()
    setEditingCategoria(categoria)
    setFormModalOpen(true)
  }

  const handleCloseForm = () => {
    setFormModalOpen(false)
    setEditingCategoria(null)
  }

  const handleOpenDelete = (categoria: CategoriaRead) => {
    deleteMutation.reset()
    setDeletingCategoria(categoria)
  }

  const handleCloseDelete = () => {
    setDeletingCategoria(null)
  }

  const handleFormSubmit = async (values: CategoriaCreate) => {
    if (editingCategoria) {
      await updateMutation.mutateAsync({ id: editingCategoria.id, data: values })
    } else {
      await createMutation.mutateAsync(values)
    }
    handleCloseForm()
  }

  const handleConfirmDelete = async () => {
    if (!deletingCategoria) return
    try {
      await deleteMutation.mutateAsync(deletingCategoria.id)
      handleCloseDelete()
    } catch {
      // El error permanece en `deleteMutation.error` para mostrarse dentro del modal.
    }
  }

  const columns = useMemo(
    () => [
      columnHelper.accessor('id', {
        header: 'ID',
        cell: (info) => <span className="font-mono text-xs text-slate-600">{info.getValue()}</span>,
      }),
      columnHelper.accessor('nombre', {
        header: 'Nombre',
        cell: (info) => <span className="font-medium text-slate-900">{info.getValue()}</span>,
      }),
      columnHelper.accessor('descripcion', {
        header: 'Descripción',
        cell: (info) => (
          <span className="text-slate-600">{info.getValue()?.trim() || 'Sin descripción'}</span>
        ),
      }),
      columnHelper.display({
        id: 'acciones',
        header: 'Acciones',
        enableSorting: false,
        cell: ({ row }) => {
          const categoria = row.original
          return (
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => handleOpenEdit(categoria)}
              >
                Editar
              </Button>
              <Button
                type="button"
                variant="danger"
                size="sm"
                onClick={() => handleOpenDelete(categoria)}
              >
                Eliminar
              </Button>
            </div>
          )
        },
      }),
    ],
    [],
  )

  const table = useReactTable({
    data: data ?? EMPTY_CATEGORIAS,
    columns,
    getRowId: (row) => String(row.id),
    state: {
      sorting,
      globalFilter,
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  const activeMutation = editingCategoria ? updateMutation : createMutation
  const rows = table.getRowModel().rows

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Administración de categorías
          </h1>
          <p className="text-sm text-slate-600">
            Creá, editá y administrá las categorías activas del catálogo.
          </p>
        </div>

        <Button type="button" variant="primary" onClick={handleOpenCreate}>
          Nueva categoría
        </Button>
      </header>

      <div className="max-w-sm">
        <Input
          label="Buscar categoría"
          placeholder="Filtrar por nombre o descripción…"
          value={globalFilter}
          onChange={(event) => setGlobalFilter(event.target.value)}
        />
      </div>

      {isLoading && !data ? (
        <Skeleton variant="row" count={5} label="Cargando categorías…" />
      ) : isError && !data ? (
        <EstadoError
          variant="alert"
          title="No se pudieron cargar las categorías"
          message={error?.message ?? 'Error al consultar las categorías.'}
          onRetry={() => void refetch()}
        />
      ) : data ? (
        <div className="space-y-4">
          {(isError || isRefetchError) && (
            <EstadoError
              variant="inline-refetch"
              title="No se pudieron actualizar las categorías; se conservan los últimos datos confirmados."
              message={error?.message ?? 'Error al actualizar las categorías.'}
              onRetry={() => void refetch()}
            />
          )}

          {rows.length === 0 ? (
            <EstadoVacio
              title={
                globalFilter.trim()
                  ? 'No se encontraron categorías con ese filtro'
                  : 'No hay categorías registradas'
              }
              description={
                globalFilter.trim()
                  ? 'Probá con otro término de búsqueda o limpiá el filtro.'
                  : 'Creá la primera categoría para comenzar a organizar los productos.'
              }
              actionLabel={globalFilter.trim() ? 'Limpiar filtro' : 'Nueva categoría'}
              onAction={
                globalFilter.trim() ? () => setGlobalFilter('') : handleOpenCreate
              }
            />
          ) : (
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
                                className="inline-flex items-center gap-1.5 font-semibold text-slate-700 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded"
                              >
                                {flexRender(
                                  header.column.columnDef.header,
                                  header.getContext(),
                                )}
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
          )}
        </div>
      ) : null}

      <CategoriaFormModal
        isOpen={formModalOpen}
        onClose={handleCloseForm}
        categoria={editingCategoria}
        onSubmit={handleFormSubmit}
        isPending={activeMutation.isPending}
        error={activeMutation.error?.message ?? null}
      />

      <Modal
        isOpen={Boolean(deletingCategoria)}
        onClose={handleCloseDelete}
        title="Eliminar categoría"
        isSubmitting={deleteMutation.isPending}
        busy={deleteMutation.isPending}
      >
        <div className="space-y-4">
          {deleteMutation.error && (
            <div
              role="alert"
              className="rounded-lg border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm font-medium text-rose-700"
            >
              {deleteMutation.error.message}
            </div>
          )}

          <p className="text-sm text-slate-700">
            ¿Confirmás la baja lógica de la categoría{' '}
            <strong>{deletingCategoria?.nombre}</strong>?
          </p>

          <div className="flex items-center justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              disabled={deleteMutation.isPending}
              onClick={handleCloseDelete}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              variant="danger"
              isLoading={deleteMutation.isPending}
              loadingText="Eliminando…"
              onClick={() => void handleConfirmDelete()}
            >
              Confirmar eliminación
            </Button>
          </div>
        </div>
      </Modal>
    </section>
  )
}
