/**
 * Página de detalle inmutable de un pedido del cliente con líneas snapshot y cancelación.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Reglas `RN-03`, `RN-04`, `RN-05`, historia `HU-TPI-03` y ruta `/mis-pedidos/:id` (págs. 5, 13–14, 18–20).
 */
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { formatPrecio } from '@/features/productos'
import { EstadoError, EstadoVacio, Skeleton } from '@/shared/components'
import { BadgeEstado, Button, Card, Modal } from '@/shared/ui'
import { useAuthSession } from '@/store/authStore'

import { useCancelarPedido } from '../hooks/useCancelarPedido'
import { usePedidoDetalle } from '../hooks/usePedidoDetalle'
import type { FormaPago, PedidoRead } from '../types/pedido.types'

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

/** Vista protegida `/mis-pedidos/:id` con metadatos, tabla snapshot y cancelación en `PENDIENTE`. */
export function PedidoDetallePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { usuario } = useAuthSession()
  const pedidoId = Number(id)
  const isValidId = Boolean(id) && Number.isInteger(pedidoId) && pedidoId > 0

  const [confirmedPedido, setConfirmedPedido] = useState<PedidoRead | undefined>(undefined)
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false)

  const { data, isLoading, isError, isRefetchError, error, refetch } =
    usePedidoDetalle(pedidoId)
  const cancelarMutation = useCancelarPedido()

  if (data && data.id === pedidoId && data !== confirmedPedido) {
    setConfirmedPedido(data)
  }

  const activePedido =
    data && data.id === pedidoId
      ? data
      : confirmedPedido && confirmedPedido.id === pedidoId
        ? confirmedPedido
        : undefined

  if (!isValidId) {
    return (
      <section className="space-y-4">
        <EstadoVacio
          title="Pedido no válido"
          description="El identificador del pedido no es válido."
          actionLabel="Volver a mis pedidos"
          onAction={() => navigate('/mis-pedidos')}
        />
      </section>
    )
  }

  function handleOpenCancelModal() {
    if (!activePedido || activePedido.estado !== 'PENDIENTE') {
      return
    }
    cancelarMutation.reset()
    setIsCancelModalOpen(true)
  }

  function handleCloseCancelModal() {
    if (cancelarMutation.isPending) {
      return
    }
    cancelarMutation.reset()
    setIsCancelModalOpen(false)
  }

  async function handleConfirmCancel() {
    if (!activePedido) {
      return
    }
    try {
      await cancelarMutation.mutateAsync(activePedido.id)
      setIsCancelModalOpen(false)
    } catch {
      // El error normalizado permanece disponible en `cancelarMutation.error` dentro del modal.
    }
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          to="/mis-pedidos"
          className="inline-flex items-center text-sm font-medium text-blue-700 hover:text-blue-800 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded"
        >
          ← Volver a mis pedidos
        </Link>
      </div>

      {isLoading && !activePedido ? (
        <Skeleton variant="card" count={2} label="Cargando detalle del pedido…" />
      ) : isError && !activePedido ? (
        <EstadoError
          variant="alert"
          title="No se pudo cargar el pedido"
          message={error?.message ?? 'Error al obtener el detalle del pedido.'}
          onRetry={() => void refetch()}
        />
      ) : !activePedido ? (
        <EstadoVacio
          title="Pedido no encontrado"
          description="No encontramos el pedido solicitado."
          actionLabel="Volver a mis pedidos"
          onAction={() => navigate('/mis-pedidos')}
        />
      ) : activePedido.usuario_id !== usuario?.id ? (
        <EstadoVacio
          title="Pedido no encontrado"
          description="No tenés permisos para consultar este pedido o el pedido no existe."
          actionLabel="Volver a mis pedidos"
          onAction={() => navigate('/mis-pedidos')}
        />
      ) : (
        <div className="space-y-6">
          {(isError || isRefetchError) && (
            <EstadoError
              variant="inline-refetch"
              isRefetchError
              message={error?.message ?? 'No se pudo actualizar el detalle del pedido.'}
              onRetry={() => void refetch()}
            />
          )}

          <header className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                  Pedido #{activePedido.id}
                </h1>
                <BadgeEstado estado={activePedido.estado} />
              </div>
              <p className="text-sm text-slate-600">
                Creado el {formatFecha(activePedido.created_at)} · Actualizado el{' '}
                {formatFecha(activePedido.updated_at)}
              </p>
            </div>

            {activePedido.estado === 'PENDIENTE' && (
              <Button variant="danger" onClick={handleOpenCancelModal}>
                Cancelar pedido
              </Button>
            )}
          </header>

          <Card className="space-y-4">
            <h2 className="text-base font-semibold text-slate-900">
              Información del pedido
            </h2>
            <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="font-medium text-slate-500">Dirección de entrega</dt>
                <dd className="mt-0.5 text-slate-900">{activePedido.direccion_entrega}</dd>
              </div>
              <div>
                <dt className="font-medium text-slate-500">Forma de pago</dt>
                <dd className="mt-0.5 text-slate-900">
                  {FORMA_PAGO_LABELS[activePedido.forma_pago]}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-slate-500">Notas</dt>
                <dd className="mt-0.5 text-slate-900">
                  {activePedido.notas?.trim() ? activePedido.notas : 'Sin notas adicionales'}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-slate-500">Total del pedido</dt>
                <dd className="mt-0.5 text-base font-bold text-slate-900">
                  {formatPrecio(activePedido.total)}
                </dd>
              </div>
            </dl>
          </Card>

          <Card className="space-y-4">
            <h2 className="text-base font-semibold text-slate-900">Detalle de productos</h2>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-600">
                    <th scope="col" className="py-2.5 pr-4 font-semibold">
                      Producto
                    </th>
                    <th scope="col" className="py-2.5 px-4 font-semibold">
                      Precio unitario
                    </th>
                    <th scope="col" className="py-2.5 px-4 font-semibold">
                      Cantidad
                    </th>
                    <th scope="col" className="py-2.5 pl-4 text-right font-semibold">
                      Subtotal
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {activePedido.items.map((item) => (
                    <tr key={`${item.producto_id}-${item.nombre_producto}`}>
                      <td className="py-3 pr-4 font-medium text-slate-900">
                        {item.nombre_producto}
                      </td>
                      <td className="py-3 px-4 text-slate-700">
                        {formatPrecio(item.precio_unitario)}
                      </td>
                      <td className="py-3 px-4 text-slate-700">{item.cantidad}</td>
                      <td className="py-3 pl-4 text-right font-semibold text-slate-900">
                        {formatPrecio(item.subtotal)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t border-slate-200">
                    <th
                      scope="row"
                      colSpan={3}
                      className="py-3 pr-4 text-right font-semibold text-slate-900"
                    >
                      Total
                    </th>
                    <td className="py-3 pl-4 text-right text-base font-bold text-slate-900">
                      {formatPrecio(activePedido.total)}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </Card>

          <Modal
            isOpen={isCancelModalOpen}
            onClose={handleCloseCancelModal}
            title={`Cancelar pedido #${activePedido.id}`}
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
                <span className="font-semibold">#{activePedido.id}</span>? Esta acción
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
        </div>
      )}
    </section>
  )
}
