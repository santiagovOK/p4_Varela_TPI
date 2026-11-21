/**
 * Página del historial de pedidos del cliente autenticado con filtro, paginación y cancelación.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Reglas `RN-03`, `RN-04`, historia `HU-TPI-03` y ruta `/mis-pedidos` (págs. 5, 13–14, 18–20).
 */
import { useState, type ChangeEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { formatPrecio } from '@/features/productos'
import { EstadoError, EstadoVacio, Paginacion, Skeleton } from '@/shared/components'
import { BadgeEstado, Button, Card, Modal } from '@/shared/ui'
import { useAuthSession } from '@/store/authStore'

import { useCancelarPedido } from '../hooks/useCancelarPedido'
import { MIS_PEDIDOS_DEFAULT_LIMIT, useMisPedidos } from '../hooks/useMisPedidos'
import type {
  EstadoPedido,
  FormaPago,
  PedidoRead,
  PedidosPaginados,
} from '../types/pedido.types'

const ESTADO_OPCIONES: ReadonlyArray<{ value: EstadoPedido; label: string }> = [
  { value: 'PENDIENTE', label: 'Pendiente' },
  { value: 'EN_PREPARACION', label: 'En preparación' },
  { value: 'ENTREGADO', label: 'Entregado' },
  { value: 'CANCELADO', label: 'Cancelado' },
]

const FORMA_PAGO_LABELS: Record<FormaPago, string> = {
  EFECTIVO: 'Efectivo',
  TRANSFERENCIA: 'Transferencia',
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

/** Vista protegida `/mis-pedidos` con historial paginado, filtro por estado y cancelación en modal. */
export function MisPedidosPage() {
  const navigate = useNavigate()
  const { usuario } = useAuthSession()
  const [estadoFiltro, setEstadoFiltro] = useState<EstadoPedido | undefined>(undefined)
  const [skip, setSkip] = useState(0)
  const [confirmedData, setConfirmedData] = useState<PedidosPaginados | undefined>(undefined)
  const [pedidoACancelar, setPedidoACancelar] = useState<PedidoRead | null>(null)
  const limit = MIS_PEDIDOS_DEFAULT_LIMIT

  const { data, isLoading, isError, isRefetchError, isPlaceholderData, error, refetch } =
    useMisPedidos({
      skip,
      limit,
      estado: estadoFiltro,
    })

  const cancelarMutation = useCancelarPedido()

  if (data && !isPlaceholderData && data !== confirmedData) {
    setConfirmedData(data)
  }

  const activeData = data ?? confirmedData

  function handleEstadoChange(event: ChangeEvent<HTMLSelectElement>) {
    const rawValue = event.target.value
    setEstadoFiltro(rawValue ? (rawValue as EstadoPedido) : undefined)
    setSkip(0)
  }

  function handleResetFilter() {
    setEstadoFiltro(undefined)
    setSkip(0)
  }

  function handleOpenCancelModal(pedido: PedidoRead) {
    if (pedido.usuario_id !== usuario?.id || pedido.estado !== 'PENDIENTE') {
      return
    }
    cancelarMutation.reset()
    setPedidoACancelar(pedido)
  }

  function handleCloseCancelModal() {
    if (cancelarMutation.isPending) {
      return
    }
    cancelarMutation.reset()
    setPedidoACancelar(null)
  }

  async function handleConfirmCancel() {
    if (
      !pedidoACancelar ||
      pedidoACancelar.usuario_id !== usuario?.id ||
      pedidoACancelar.estado !== 'PENDIENTE'
    ) {
      return
    }
    try {
      await cancelarMutation.mutateAsync(pedidoACancelar.id)
      setPedidoACancelar(null)
    } catch {
      // El error normalizado permanece disponible en `cancelarMutation.error` dentro del modal.
    }
  }

  return (
    <section className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Mis pedidos</h1>
        <p className="text-sm text-slate-600">
          Consultá el historial de tus compras, revisá su detalle y cancelá pedidos pendientes.
        </p>
      </header>

      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-end">
        <div className="w-full space-y-1.5 sm:w-64">
          <label
            htmlFor="mis-pedidos-estado-select"
            className="block text-sm font-medium text-slate-700"
          >
            Filtrar por estado
          </label>
          <select
            id="mis-pedidos-estado-select"
            value={estadoFiltro ?? ''}
            onChange={handleEstadoChange}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-1"
          >
            <option value="">Todos los estados</option>
            {ESTADO_OPCIONES.map((opcion) => (
              <option key={opcion.value} value={opcion.value}>
                {opcion.label}
              </option>
            ))}
          </select>
        </div>

        {estadoFiltro !== undefined && (
          <Button variant="secondary" onClick={handleResetFilter}>
            Limpiar filtro
          </Button>
        )}
      </div>

      {isLoading && !activeData ? (
        <Skeleton variant="row" count={4} label="Cargando tus pedidos…" />
      ) : isError && !activeData ? (
        <EstadoError
          variant="alert"
          title="No se pudieron cargar tus pedidos"
          message={error?.message ?? 'Error al consultar tu historial de pedidos.'}
          onRetry={() => void refetch()}
        />
      ) : activeData ? (
        <div className="space-y-5">
          {(isError || isRefetchError) && (
            <EstadoError
              variant="inline-refetch"
              isRefetchError
              message={error?.message ?? 'No se pudo actualizar el listado de pedidos.'}
              onRetry={() => void refetch()}
            />
          )}

          {activeData.items.length === 0 ? (
            <EstadoVacio
              title={
                estadoFiltro !== undefined
                  ? 'No hay pedidos con el estado seleccionado'
                  : 'Todavía no realizaste pedidos'
              }
              description={
                estadoFiltro !== undefined
                  ? 'Probá quitando el filtro para ver todo tu historial.'
                  : 'Explorá el catálogo para agregar productos y confirmar tu primera compra.'
              }
              actionLabel={
                estadoFiltro !== undefined ? 'Ver todos los pedidos' : 'Ir al catálogo'
              }
              onAction={
                estadoFiltro !== undefined ? handleResetFilter : () => navigate('/')
              }
            />
          ) : (
            <>
              <div className="space-y-3">
                {activeData.items.map((pedido) => {
                  const totalUnidades = pedido.items.reduce(
                    (acc, item) => acc + item.cantidad,
                    0,
                  )

                  return (
                    <Card key={pedido.id} className="space-y-3">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex flex-wrap items-center gap-2.5">
                            <h2 className="text-base font-semibold text-slate-900">
                              Pedido #{pedido.id}
                            </h2>
                            <BadgeEstado estado={pedido.estado} />
                          </div>
                          <p className="text-xs text-slate-500">
                            Realizado el {formatFecha(pedido.created_at)}
                          </p>
                        </div>

                        <p className="text-lg font-bold text-slate-900">
                          {formatPrecio(pedido.total)}
                        </p>
                      </div>

                      <div className="grid grid-cols-1 gap-2 border-t border-slate-100 pt-3 text-sm text-slate-600 sm:grid-cols-3">
                        <div>
                          <span className="font-medium text-slate-700">Entrega: </span>
                          {pedido.direccion_entrega}
                        </div>
                        <div>
                          <span className="font-medium text-slate-700">Pago: </span>
                          {FORMA_PAGO_LABELS[pedido.forma_pago]}
                        </div>
                        <div>
                          <span className="font-medium text-slate-700">Ítems: </span>
                          {totalUnidades} {totalUnidades === 1 ? 'unidad' : 'unidades'}
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-100 pt-3">
                        <Link
                          to={`/mis-pedidos/${pedido.id}`}
                          aria-label={`Ver detalle del pedido #${pedido.id}`}
                          className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-800 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-1"
                        >
                          Ver detalle
                        </Link>

                        {pedido.usuario_id === usuario?.id && pedido.estado === 'PENDIENTE' && (
                          <Button
                            variant="danger"
                            size="sm"
                            aria-label={`Cancelar pedido #${pedido.id}`}
                            onClick={() => handleOpenCancelModal(pedido)}
                          >
                            Cancelar pedido
                          </Button>
                        )}
                      </div>
                    </Card>
                  )
                })}
              </div>

              <Paginacion
                total={activeData.total}
                skip={skip}
                limit={limit}
                onPageChange={setSkip}
              />
            </>
          )}
        </div>
      ) : null}

      <Modal
        isOpen={Boolean(
          pedidoACancelar &&
            pedidoACancelar.usuario_id === usuario?.id &&
            pedidoACancelar.estado === 'PENDIENTE',
        )}
        onClose={handleCloseCancelModal}
        title={pedidoACancelar ? `Cancelar pedido #${pedidoACancelar.id}` : 'Cancelar pedido'}
        isSubmitting={cancelarMutation.isPending}
        busy={cancelarMutation.isPending}
        footer={
          <>
            <Button
              variant="secondary"
              size="sm"
              disabled={cancelarMutation.isPending}
              onClick={handleCloseCancelModal}
            >
              Volver
            </Button>
            <Button
              variant="danger"
              size="sm"
              isLoading={cancelarMutation.isPending}
              onClick={() => void handleConfirmCancel()}
            >
              Confirmar cancelación
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-slate-700">
            ¿Confirmás la cancelación del pedido{' '}
            <span className="font-semibold">#{pedidoACancelar?.id}</span>? Esta acción
            restituirá el stock de los productos incluidos y no se puede deshacer.
          </p>

          {cancelarMutation.isError && (
            <div
              role="alert"
              className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800"
            >
              {cancelarMutation.error?.message ?? 'No se pudo cancelar el pedido.'}
            </div>
          )}
        </div>
      </Modal>
    </section>
  )
}
