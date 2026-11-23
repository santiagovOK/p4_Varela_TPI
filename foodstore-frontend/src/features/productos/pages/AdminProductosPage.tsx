/**
 * Página administrativa `/admin/productos` con TanStack Table, paginación local, filtros y modales ABM/Stock (`HU-TPI-04`).
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Ruta `/admin/productos`, sección "Tablas" (`@tanstack/react-table`) y "Estado, datos y sesión" (págs. 18–20).
 */
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type PaginationState,
  type SortingState,
  useReactTable,
} from '@tanstack/react-table'
import { useId, useMemo, useState } from 'react'

import { useCategorias } from '@/features/categorias'
import { EstadoError, EstadoVacio, Skeleton } from '@/shared/components'
import { Button, Input, Modal } from '@/shared/ui'

import { formatPrecio, isValidImageUrl } from '../components/ProductoCard'
import { ProductoFormModal } from '../components/ProductoFormModal'
import { StockModal } from '../components/StockModal'
import { useAdminProductos } from '../hooks/useAdminProductos'
import type {
  ProductoCreate,
  ProductoRead,
  ProductoStockUpdate,
} from '../types/producto.types'

const EMPTY_PRODUCTOS: ProductoRead[] = []
const ADMIN_TABLE_PAGE_SIZE = 10
const columnHelper = createColumnHelper<ProductoRead>()

function mapAriaSort(sortDirection: false | 'asc' | 'desc'): 'ascending' | 'descending' | 'none' {
  if (sortDirection === 'asc') return 'ascending'
  if (sortDirection === 'desc') return 'descending'
  return 'none'
}

/** Panel administrativo de productos con ordenamiento, filtros, paginación local y modales de producto/stock. */
export function AdminProductosPage() {
  const categoriaFilterId = useId()
  const {
    productosQuery,
    createMutation,
    updateMutation,
    updateStockMutation,
    deleteMutation,
  } = useAdminProductos()
  const categoriasQuery = useCategorias()

  const { data, isLoading, isError, isRefetchError, error, refetch } = productosQuery
  const categorias = categoriasQuery.data ?? []

  const [sorting, setSorting] = useState<SortingState>([])
  const [searchFilter, setSearchFilter] = useState('')
  const [categoriaFilter, setCategoriaFilter] = useState<string>('')
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: ADMIN_TABLE_PAGE_SIZE,
  })

  const [formModalOpen, setFormModalOpen] = useState(false)
  const [editingProducto, setEditingProducto] = useState<ProductoRead | null>(null)
  const [stockProducto, setStockProducto] = useState<ProductoRead | null>(null)
  const [deletingProducto, setDeletingProducto] = useState<ProductoRead | null>(null)
  const [failedImages, setFailedImages] = useState<Record<number, string>>({})

  const handleSearchChange = (value: string) => {
    setSearchFilter(value)
    setPagination((prev) => ({ ...prev, pageIndex: 0 }))
  }

  const handleCategoriaFilterChange = (value: string) => {
    setCategoriaFilter(value)
    setPagination((prev) => ({ ...prev, pageIndex: 0 }))
  }

  const handleResetFilters = () => {
    setSearchFilter('')
    setCategoriaFilter('')
    setPagination((prev) => ({ ...prev, pageIndex: 0 }))
  }

  const handleOpenCreate = () => {
    createMutation.reset()
    updateMutation.reset()
    setEditingProducto(null)
    setFormModalOpen(true)
  }

  const handleOpenEdit = (producto: ProductoRead) => {
    createMutation.reset()
    updateMutation.reset()
    setEditingProducto(producto)
    setFormModalOpen(true)
  }

  const handleCloseForm = () => {
    setFormModalOpen(false)
    setEditingProducto(null)
  }

  const handleOpenStock = (producto: ProductoRead) => {
    updateStockMutation.reset()
    setStockProducto(producto)
  }

  const handleCloseStock = () => {
    setStockProducto(null)
  }

  const handleOpenDelete = (producto: ProductoRead) => {
    deleteMutation.reset()
    setDeletingProducto(producto)
  }

  const handleCloseDelete = () => {
    setDeletingProducto(null)
  }

  const handleFormSubmit = async (values: ProductoCreate) => {
    if (editingProducto) {
      await updateMutation.mutateAsync({ id: editingProducto.id, data: values })
    } else {
      await createMutation.mutateAsync(values)
    }
    handleCloseForm()
  }

  const handleStockSubmit = async (values: ProductoStockUpdate) => {
    if (!stockProducto) return
    await updateStockMutation.mutateAsync({ id: stockProducto.id, data: values })
    handleCloseStock()
  }

  const handleConfirmDelete = async () => {
    if (!deletingProducto) return
    try {
      await deleteMutation.mutateAsync(deletingProducto.id)
      handleCloseDelete()
    } catch {
      // El error permanece en `deleteMutation.error` para mostrarse dentro del modal.
    }
  }

  const rawItems = data?.items ?? EMPTY_PRODUCTOS

  const filteredProductos = useMemo(() => {
    const normalizedSearch = searchFilter.trim().toLowerCase()
    const selectedCategoriaId = categoriaFilter ? Number(categoriaFilter) : null

    if (!normalizedSearch && !selectedCategoriaId) {
      return rawItems
    }

    return rawItems.filter((item) => {
      if (selectedCategoriaId && item.categoria_id !== selectedCategoriaId) {
        return false
      }
      if (normalizedSearch) {
        const matchNombre = item.nombre.toLowerCase().includes(normalizedSearch)
        const matchDescripcion = item.descripcion?.toLowerCase().includes(normalizedSearch) ?? false
        const matchCategoria = item.categoria?.nombre.toLowerCase().includes(normalizedSearch) ?? false
        return matchNombre || matchDescripcion || matchCategoria
      }
      return true
    })
  }, [rawItems, searchFilter, categoriaFilter])

  const columns = useMemo(
    () => [
      columnHelper.display({
        id: 'imagen',
        header: 'Imagen',
        enableSorting: false,
        cell: ({ row }) => {
          const producto = row.original
          const normalizedUrl = producto.imagen_url?.trim() ?? null
          const canShow =
            isValidImageUrl(normalizedUrl) && failedImages[producto.id] !== normalizedUrl

          return canShow ? (
            <img
              src={normalizedUrl}
              alt={producto.nombre}
              className="h-10 w-10 rounded-lg border border-slate-200 object-cover"
              onError={() =>
                setFailedImages((prev) => ({
                  ...prev,
                  [producto.id]: normalizedUrl,
                }))
              }
            />
          ) : (
            <div
              aria-hidden="true"
              className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-slate-100 text-[10px] font-medium text-slate-400"
            >
              Sin img
            </div>
          )
        },
      }),
      columnHelper.accessor('nombre', {
        header: 'Nombre',
        cell: (info) => <span className="font-medium text-slate-900">{info.getValue()}</span>,
      }),
      columnHelper.accessor((row) => row.categoria?.nombre ?? 'Sin categoría', {
        id: 'categoria',
        header: 'Categoría',
        cell: (info) => <span className="text-slate-700">{info.getValue()}</span>,
      }),
      columnHelper.accessor('precio_base', {
        header: 'Precio',
        cell: (info) => (
          <span className="font-medium text-slate-900">{formatPrecio(info.getValue())}</span>
        ),
      }),
      columnHelper.accessor('stock', {
        header: 'Stock',
        cell: (info) => <span className="font-mono text-slate-800">{info.getValue()}</span>,
      }),
      columnHelper.accessor('disponible', {
        header: 'Disponible',
        cell: (info) => {
          const disponible = info.getValue()
          return (
            <span
              className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                disponible
                  ? 'border-emerald-300 bg-emerald-100 text-emerald-800'
                  : 'border-rose-300 bg-rose-100 text-rose-800'
              }`}
            >
              {disponible ? 'Disponible' : 'No disponible'}
            </span>
          )
        },
      }),
      columnHelper.display({
        id: 'acciones',
        header: 'Acciones',
        enableSorting: false,
        cell: ({ row }) => {
          const producto = row.original
          return (
            <div className="flex flex-wrap items-center gap-1.5">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => handleOpenEdit(producto)}
              >
                Editar
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => handleOpenStock(producto)}
              >
                Stock
              </Button>
              <Button
                type="button"
                variant="danger"
                size="sm"
                onClick={() => handleOpenDelete(producto)}
              >
                Eliminar
              </Button>
            </div>
          )
        },
      }),
    ],
    [failedImages],
  )

  const table = useReactTable({
    data: filteredProductos,
    columns,
    getRowId: (row) => String(row.id),
    state: {
      sorting,
      pagination,
    },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  })

  const activeMutation = editingProducto ? updateMutation : createMutation
  const rows = table.getRowModel().rows
  const pageCount = Math.max(1, table.getPageCount())
  const hasActiveFilters = Boolean(searchFilter.trim() || categoriaFilter)

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Administración de productos
          </h1>
          <p className="text-sm text-slate-600">
            Gestioná el catálogo, precios, categorías, stock y disponibilidad de productos.
          </p>
        </div>

        <Button type="button" variant="primary" onClick={handleOpenCreate}>
          Nuevo producto
        </Button>
      </header>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:max-w-2xl">
        <Input
          label="Buscar producto"
          placeholder="Buscar por nombre, descripción o categoría…"
          value={searchFilter}
          onChange={(event) => handleSearchChange(event.target.value)}
        />

        <div className="space-y-1.5">
          <label htmlFor={categoriaFilterId} className="block text-sm font-medium text-slate-700">
            Filtrar por categoría
          </label>
          <select
            id={categoriaFilterId}
            value={categoriaFilter}
            onChange={(event) => handleCategoriaFilterChange(event.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-1"
          >
            <option value="">Todas las categorías</option>
            {categorias.map((cat) => (
              <option key={cat.id} value={String(cat.id)}>
                {cat.nombre}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading && !data ? (
        <Skeleton variant="row" count={6} label="Cargando productos…" />
      ) : isError && !data ? (
        <EstadoError
          variant="alert"
          title="No se pudieron cargar los productos"
          message={error?.message ?? 'Error al consultar los productos.'}
          onRetry={() => void refetch()}
        />
      ) : data ? (
        <div className="space-y-4">
          {(isError || isRefetchError) && (
            <EstadoError
              variant="inline-refetch"
              title="No se pudieron actualizar los productos; se conservan los últimos datos confirmados."
              message={error?.message ?? 'Error al actualizar los productos.'}
              onRetry={() => void refetch()}
            />
          )}

          {rows.length === 0 ? (
            <EstadoVacio
              title={
                hasActiveFilters
                  ? 'No se encontraron productos con esos filtros'
                  : 'No hay productos registrados'
              }
              description={
                hasActiveFilters
                  ? 'Probá modificando la búsqueda o la categoría seleccionada.'
                  : 'Creá el primer producto para poblar el catálogo.'
              }
              actionLabel={hasActiveFilters ? 'Limpiar filtros' : 'Nuevo producto'}
              onAction={hasActiveFilters ? handleResetFilters : handleOpenCreate}
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

              <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                <p className="text-sm text-slate-600">
                  Página {pagination.pageIndex + 1} de {pageCount} ({filteredProductos.length}{' '}
                  productos)
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
      ) : null}

      <ProductoFormModal
        isOpen={formModalOpen}
        onClose={handleCloseForm}
        producto={editingProducto}
        categorias={categorias}
        onSubmit={handleFormSubmit}
        isPending={activeMutation.isPending}
        error={activeMutation.error?.message ?? null}
      />

      <StockModal
        isOpen={Boolean(stockProducto)}
        onClose={handleCloseStock}
        producto={stockProducto}
        onSubmit={handleStockSubmit}
        isPending={updateStockMutation.isPending}
        error={updateStockMutation.error?.message ?? null}
      />

      <Modal
        isOpen={Boolean(deletingProducto)}
        onClose={handleCloseDelete}
        title="Eliminar producto"
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
            ¿Confirmás la baja lógica del producto <strong>{deletingProducto?.nombre}</strong>?
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
