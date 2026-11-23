/**
 * Página administrativa `/admin/pedidos` con TanStack Table, filtros, máquina de estados `RN-02`
 * y modal de detalle snapshot `RN-05` (`HU-TPI-05`).
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Ruta `/admin/pedidos`, reglas `RN-02`, `RN-03`, `RN-05` y sección "Tablas" (págs. 5, 14, 18–20).
 */
import {
  type ColumnFiltersState,
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type PaginationState,
  type SortingState,
  useReactTable,
} from '@tanstack/react-table'
import { useCallback, useId, useMemo, useState } from 'react'

import { formatPrecio } from '@/features/productos'
import { EstadoError, EstadoVacio, Skeleton } from '@/shared/components'
import { BadgeEstado, Button, Input, Modal } from '@/shared/ui'

import { useAdminPedidos } from '../hooks/useAdminPedidos'
import type { EstadoPedido, FormaPago, PedidoRead } from '../types/pedido.types'

const EMPTY_PEDIDOS: PedidoRead[] = []
const ADMIN_PEDIDOS_PAGE_SIZE = 10
const columnHelper = createColumnHelper<PedidoRead>()

type EstadoFiltro = 'TODOS' | EstadoPedido

const ESTADO_OPCIONES: Array<{ value: EstadoFiltro; label: string }> = [
  { value: 'TODOS', label: 'Todos los estados' },
  { value: 'PENDIENTE', label: 'Pendiente' },
  { value: 'EN_PREPARACION', label: 'En preparación' },
  { value: 'ENTREGADO', label: 'Entregado' },
  { value: 'CANCELADO', label: 'Cancelado' },
]

const FORMA_PAGO_LABELS: Record<FormaPago, string> = {
  EFECTIVO: 'Efectivo',
  TRANSFERENCIA: 'Transferencia',
}

function mapAriaSort(sortDirection: false | 'asc' | 'desc'): 'ascending' | 'descending' | 'none' {
  if (sortDirection === 'asc') return 'ascending'
  if (sortDirection === 'desc') return 'descending'
  return 'none'
}

function formatFecha(isoDate: string): string {
  const parsed = new Date(isoDate)
  if (Number.isNaN(parsed.getTime())) {
    return isoDate
  }
  return new Intl.DateTimeFormat('es-AR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(parsed)
}

/** Panel administrativo de pedidos con tabla ordenable, filtros, transiciones `RN-02` y detalle `RN-05`. */
export function AdminPedidosPage() {
  const estadoFilterId = useId()
  const { pedidosQuery, cambiarEstadoMutation } = useAdminPedidos()
  const { data, isLoading, isError, isRefetchError, error, refetch } = pedidosQuery

  const [sorting, setSorting] = useState<SortingState>([])
  const [estadoFilter, setEstadoFilter] = useState<EstadoFiltro>('TODOS')
  const [searchFilter, setSearchFilter] = useState('')
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: ADMIN_PEDIDOS_PAGE_SIZE,
  })
  const [selectedPedido, setSelectedPedido] = useState<PedidoRead | null>(null)
  const [pendingActionKey, setPendingActionKey] = useState<string | null>(null)

  const rawItems = data?.items ?? EMPTY_PEDIDOS

  const handleEstadoFilterChange = (value: EstadoFiltro) => {
    setEstadoFilter(value)
    setPagination((prev) => ({ ...prev, pageIndex: 0 }))
  }

  const handleSearchChange = (value: string) => {
    setSearchFilter(value)
    setPagination((prev) => ({ ...prev, pageIndex: 0 }))
  }

  const handleResetFilters = () => {
    setEstadoFilter('TODOS')
    setSearchFilter('')
    setPagination((prev) => ({ ...prev, pageIndex: 0 }))
  }

  const handleTransicion = useCallback(
    async (pedidoId: number, nuevoEstado: EstadoPedido) => {
      const actionKey = `${pedidoId}-${nuevoEstado}`
      setPendingActionKey(actionKey)
      try {
        await cambiarEstadoMutation.mutateAsync({ id: pedidoId, estado: nuevoEstado })
      } catch {
        // El error normalizado permanece en `cambiarEstadoMutation.error` para mostrarse en `role="alert"`.
      } finally {
        setPendingActionKey(null)
      }
    },
    [cambiarEstadoMutation],
  )

  const columnFilters = useMemo<ColumnFiltersState>(() => {
    if (estadoFilter === 'TODOS') {
      return []
    }
    return [{ id: 'estado', value: estadoFilter }]
  }, [estadoFilter])

  const columns = useMemo(
    () => [
      columnHelper.accessor('id', {
        header: 'Pedido',
        cell: (info) => <span className="font-semibold text-slate-900">#{info.getValue()}</span>,
      }),
      columnHelper.accessor('usuario_id', {
        header: 'Usuario',
        cell: (info) => <span className="text-slate-700">#{info.getValue()}</span>,
      }),
      columnHelper.accessor('created_at', {
        header: 'Fecha',
        cell: (info) => (
          <span className="whitespace-nowrap text-slate-700">{formatFecha(info.getValue())}</span>
        ),
      }),
      columnHelper.accessor('estado', {
        header: 'Estado',
        filterFn: 'equalsString',
        cell: (info) => <BadgeEstado estado={info.getValue()} />,
      }),
      columnHelper.accessor('forma_pago', {
        header: 'Pago',
        cell: (info) => (
          <span className="text-slate-700">{FORMA_PAGO_LABELS[info.getValue()]}</span>
        ),
      }),
      columnHelper.accessor('total', {
        header: 'Total',
        cell: (info) => (
          <span className="font-medium text-slate-900">{formatPrecio(info.getValue())}</span>
        ),
      }),
      columnHelper.display({
        id: 'acciones',
        header: 'Acciones',
        enableSorting: false,
        cell: ({ row }) => {
          const pedido = row.original
          const isMutating = cambiarEstadoMutation.isPending
          const isAdvancing =
            isMutating && pendingActionKey === `${pedido.id}-EN_PREPARACION`
          const isDelivering =
            isMutating && pendingActionKey === `${pedido.id}-ENTREGADO`
          const isCancelling =
            isMutating && pendingActionKey === `${pedido.id}-CANCELADO`

          return (
            <div className="flex flex-wrap items-center gap-1.5">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => setSelectedPedido(pedido)}
              >
                Ver detalle
              </Button>

              {pedido.estado === 'PENDIENTE' && (
                <>
                  <Button
                    type="button"
                    variant="primary"
                    size="sm"
                    disabled={isMutating}
                    isLoading={isAdvancing}
                    loadingText="Actualizando…"
                    onClick={() => void handleTransicion(pedido.id, 'EN_PREPARACION')}
                  >
                    Avanzar a En preparación
                  </Button>
                  <Button
                    type="button"
                    variant="danger"
                    size="sm"
                    disabled={isMutating}
                    isLoading={isCancelling}
                    loadingText="Cancelando…"
                    onClick={() => void handleTransicion(pedido.id, 'CANCELADO')}
                  >
                    Cancelar
                  </Button>
                </>
              )}

              {pedido.estado === 'EN_PREPARACION' && (
                <>
                  <Button
                    type="button"
                    variant="primary"
                    size="sm"
                    disabled={isMutating}
                    isLoading={isDelivering}
                    loadingText="Actualizando…"
                    onClick={() => void handleTransicion(pedido.id, 'ENTREGADO')}
                  >
                    Marcar Entregado
                  </Button>
                  <Button
                    type="button"
                    variant="danger"
                    size="sm"
                    disabled={isMutating}
                    isLoading={isCancelling}
                    loadingText="Cancelando…"
                    onClick={() => void handleTransicion(pedido.id, 'CANCELADO')}
                  >
                    Cancelar
                  </Button>
                </>
              )}
            </div>
          )
        },
      }),
    ],
    [cambiarEstadoMutation.isPending, handleTransicion, pendingActionKey],
  )

  const table = useReactTable({
    data: rawItems,
    columns,
    getRowId: (row) => String(row.id),
    state: {
      sorting,
      columnFilters,
      globalFilter: searchFilter,
      pagination,
    },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    globalFilterFn: (row, _columnId, filterValue) => {
      const term = String(filterValue ?? '')
        .trim()
        .toLowerCase()
      if (!term) return true
      const pedido = row.original
      const matchId = `#${pedido.id}`.includes(term) || String(pedido.id).includes(term)
      const matchUsuario = String(pedido.usuario_id).includes(term)
      const matchDireccion = pedido.direccion_entrega.toLowerCase().includes(term)
      const matchPago = FORMA_PAGO_LABELS[pedido.forma_pago].toLowerCase().includes(term)
      const matchNotas = pedido.notas?.toLowerCase().includes(term) ?? false
      const matchItems = pedido.items.some((item) =>
        item.nombre_producto.toLowerCase().includes(term),
      )
      return matchId || matchUsuario || matchDireccion || matchPago || matchNotas || matchItems
    },
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  })

  const rows = table.getRowModel().rows
  const filteredCount = table.getFilteredRowModel().rows.length
  const pageCount = Math.max(1, table.getPageCount())
  const hasActiveFilters = estadoFilter !== 'TODOS' || Boolean(searchFilter.trim())

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Administración de pedidos
          </h1>
          <p className="text-sm text-slate-600">
            Supervisá los pedidos recibidos, consultá su detalle y ejecutá transiciones de estado.
          </p>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:max-w-2xl">
        <Input
          label="Buscar pedido"
          placeholder="Buscar por #ID, dirección, producto o notas…"
          value={searchFilter}
          onChange={(event) => handleSearchChange(event.target.value)}
        />

        <div className="space-y-1.5">
          <label htmlFor={estadoFilterId} className="block text-sm font-medium text-slate-700">
            Filtrar por estado
          </label>
          <select
            id={estadoFilterId}
            value={estadoFilter}
            onChange={(event) => handleEstadoFilterChange(event.target.value as EstadoFiltro)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-1"
          >
            {ESTADO_OPCIONES.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {cambiarEstadoMutation.error && (
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-800"
        >
          <span>{cambiarEstadoMutation.error.message}</span>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => cambiarEstadoMutation.reset()}
          >
            Cerrar aviso
          </Button>
        </div>
      )}

      {isLoading && !data ? (
        <Skeleton variant="row" count={6} label="Cargando pedidos…" />
      ) : isError && !data ? (
        <EstadoError
          variant="alert"
          title="No se pudieron cargar los pedidos"
          message={error?.message ?? 'Error al consultar los pedidos.'}
          onRetry={() => void refetch()}
        />
      ) : data ? (
        <div className="space-y-4">
          {(isError || isRefetchError) && (
            <EstadoError
              variant="inline-refetch"
              title="No se pudieron actualizar los pedidos; se conservan los últimos datos confirmados."
              message={error?.message ?? 'Error al actualizar los pedidos.'}
              onRetry={() => void refetch()}
            />
          )}

          {rows.length === 0 ? (
            <EstadoVacio
              title={
                hasActiveFilters
                  ? 'No se encontraron pedidos con esos filtros'
                  : 'No hay pedidos registrados'
              }
              description={
                hasActiveFilters
                  ? 'Probá modificando el estado seleccionado o el término de búsqueda.'
                  : 'Cuando los clientes realicen compras aparecerán aquí para su gestión.'
              }
              actionLabel={hasActiveFilters ? 'Limpiar filtros' : undefined}
              onAction={hasActiveFilters ? handleResetFilters : undefined}
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
                  Página {pagination.pageIndex + 1} de {pageCount} ({filteredCount} pedidos)
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

      <Modal
        isOpen={Boolean(selectedPedido)}
        onClose={() => setSelectedPedido(null)}
        title={selectedPedido ? `Detalle del pedido #${selectedPedido.id}` : 'Detalle del pedido'}
        footer={
          <Button type="button" variant="secondary" onClick={() => setSelectedPedido(null)}>
            Cerrar
          </Button>
        }
      >
        {selectedPedido && (
          <div className="space-y-4 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <BadgeEstado estado={selectedPedido.estado} />
              <span className="text-slate-600">{formatFecha(selectedPedido.created_at)}</span>
            </div>

            <dl className="grid grid-cols-1 gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 sm:grid-cols-2">
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Usuario
                </dt>
                <dd className="font-medium text-slate-900">#{selectedPedido.usuario_id}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Forma de pago
                </dt>
                <dd className="font-medium text-slate-900">
                  {FORMA_PAGO_LABELS[selectedPedido.forma_pago]}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Dirección de entrega
                </dt>
                <dd className="font-medium text-slate-900">{selectedPedido.direccion_entrega}</dd>
              </div>
              {selectedPedido.notas && (
                <div className="sm:col-span-2">
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Notas
                  </dt>
                  <dd className="text-slate-800">{selectedPedido.notas}</dd>
                </div>
              )}
            </dl>

            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200 text-left text-xs sm:text-sm">
                <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-600">
                  <tr>
                    <th scope="col" className="px-3 py-2">
                      Producto
                    </th>
                    <th scope="col" className="px-3 py-2 text-right">
                      Precio unit.
                    </th>
                    <th scope="col" className="px-3 py-2 text-right">
                      Cant.
                    </th>
                    <th scope="col" className="px-3 py-2 text-right">
                      Subtotal
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {selectedPedido.items.map((item) => (
                    <tr key={item.producto_id}>
                      <td className="px-3 py-2 font-medium text-slate-900">
                        {item.nombre_producto}
                      </td>
                      <td className="px-3 py-2 text-right text-slate-700">
                        {formatPrecio(item.precio_unitario)}
                      </td>
                      <td className="px-3 py-2 text-right font-mono text-slate-800">
                        {item.cantidad}
                      </td>
                      <td className="px-3 py-2 text-right font-medium text-slate-900">
                        {formatPrecio(item.subtotal)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="border-t border-slate-200 bg-slate-50">
                  <tr>
                    <th
                      scope="row"
                      colSpan={3}
                      className="px-3 py-2 text-right font-semibold text-slate-700"
                    >
                      Total
                    </th>
                    <td className="px-3 py-2 text-right font-bold text-slate-900">
                      {formatPrecio(selectedPedido.total)}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}
      </Modal>
    </section>
  )
}
