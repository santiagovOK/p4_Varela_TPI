/**
 * Pantalla pública del carrito de compras (`/carrito`) conectada a `cartStore`.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - HU-TPI-02, HU-TPI-03 y tabla "Rutas y pantallas" (`/carrito`, págs. 18–20).
 */
import { useNavigate } from 'react-router-dom'

import { formatPrecio } from '@/features/productos'
import { EstadoVacio } from '@/shared/components'
import { Button, Card } from '@/shared/ui'
import {
  useCartActions,
  useCartCount,
  useCartItems,
  useCartTotal,
} from '@/store/cartStore'

/** Permite visualizar, ajustar cantidades, quitar ítems, vaciar el carrito o avanzar al checkout. */
export function CarritoPage() {
  const navigate = useNavigate()
  const items = useCartItems()
  const total = useCartTotal()
  const totalItems = useCartCount()
  const { cambiarCantidad, quitar, vaciar } = useCartActions()

  if (items.length === 0) {
    return (
      <section className="mx-auto max-w-4xl space-y-6 py-4">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Carrito de compras
          </h1>
          <p className="text-sm text-slate-600">
            Revisá los productos seleccionados antes de confirmar tu pedido.
          </p>
        </header>

        <EstadoVacio
          title="El carrito está vacío"
          description="Agregá productos desde el catálogo para armar tu pedido."
          actionLabel="Ir al catálogo"
          onAction={() => navigate('/')}
        />
      </section>
    )
  }

  return (
    <section className="mx-auto max-w-5xl space-y-6 py-4">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Carrito de compras
          </h1>
          <p className="text-sm text-slate-600">
            {totalItems === 1
              ? '1 unidad seleccionada en tu pedido.'
              : `${totalItems} unidades seleccionadas en tu pedido.`}
          </p>
        </div>

        <Button
          variant="secondary"
          size="sm"
          aria-label="Vaciar carrito"
          onClick={vaciar}
        >
          Vaciar carrito
        </Button>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th scope="col" className="pb-3 pr-4">
                    Producto
                  </th>
                  <th scope="col" className="pb-3 px-3">
                    Precio unitario
                  </th>
                  <th scope="col" className="pb-3 px-3">
                    Cantidad
                  </th>
                  <th scope="col" className="pb-3 px-3 text-right">
                    Subtotal
                  </th>
                  <th scope="col" className="pb-3 pl-3 text-right">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((item) => {
                  const subtotal =
                    Math.round(item.precio_unitario * item.cantidad * 100) / 100

                  return (
                    <tr key={item.producto_id} className="align-middle">
                      <td className="py-4 pr-4 font-medium text-slate-900">
                        {item.nombre}
                      </td>
                      <td className="py-4 px-3 whitespace-nowrap text-slate-600">
                        {formatPrecio(item.precio_unitario)}
                      </td>
                      <td className="py-4 px-3">
                        <div className="inline-flex items-center gap-1.5">
                          <Button
                            variant="secondary"
                            size="sm"
                            aria-label={`Disminuir cantidad de ${item.nombre}`}
                            onClick={() =>
                              cambiarCantidad(item.producto_id, item.cantidad - 1)
                            }
                          >
                            -
                          </Button>
                          <input
                            type="number"
                            min={1}
                            step={1}
                            aria-label={`Cantidad de ${item.nombre}`}
                            value={item.cantidad}
                            onChange={(event) => {
                              const parsed = Number.parseInt(event.target.value, 10)
                              if (Number.isFinite(parsed) && parsed >= 1) {
                                cambiarCantidad(item.producto_id, parsed)
                              }
                            }}
                            className="w-16 rounded-lg border border-slate-300 bg-white px-2 py-1 text-center text-sm text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                          />
                          <Button
                            variant="secondary"
                            size="sm"
                            aria-label={`Aumentar cantidad de ${item.nombre}`}
                            onClick={() =>
                              cambiarCantidad(item.producto_id, item.cantidad + 1)
                            }
                          >
                            +
                          </Button>
                        </div>
                      </td>
                      <td className="py-4 px-3 text-right font-semibold whitespace-nowrap text-slate-900">
                        {formatPrecio(subtotal)}
                      </td>
                      <td className="py-4 pl-3 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          aria-label={`Quitar ${item.nombre} del carrito`}
                          onClick={() => quitar(item.producto_id)}
                        >
                          Quitar
                        </Button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Resumen del carrito" className="h-fit">
          <dl className="space-y-2 text-sm">
            <div className="flex items-center justify-between text-slate-600">
              <dt>Unidades totales</dt>
              <dd className="font-medium text-slate-900">{totalItems}</dd>
            </div>
            <div className="flex items-center justify-between border-t border-slate-100 pt-3 text-base font-bold text-slate-900">
              <dt>Total</dt>
              <dd>{formatPrecio(total)}</dd>
            </div>
          </dl>

          <div className="mt-5 flex flex-col gap-2.5">
            <Button
              variant="primary"
              className="w-full"
              onClick={() => navigate('/checkout')}
            >
              Continuar al checkout
            </Button>
            <Button
              variant="secondary"
              className="w-full"
              onClick={() => navigate('/')}
            >
              Seguir comprando
            </Button>
          </div>
        </Card>
      </div>
    </section>
  )
}
