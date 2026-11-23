/**
 * Página protegida de confirmación de pedido (`/checkout`) con `@tanstack/react-form`.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Reglas `RN-01`, `RN-05`, `RN-06`, `HU-TPI-03` y tablas de rutas/formularios (págs. 5, 13–14, 18–20).
 */
import { useId } from 'react'
import { useForm } from '@tanstack/react-form'
import { Link, useNavigate } from 'react-router-dom'

import { formatPrecio } from '@/features/productos'
import { EstadoVacio } from '@/shared/components'
import { Button, Card, Input } from '@/shared/ui'
import {
  useCartActions,
  useCartCount,
  useCartItems,
  useCartTotal,
} from '@/store/cartStore'

import { useCrearPedido } from '../hooks/useCrearPedido'
import type { FormaPago, PedidoCreate } from '../types/pedido.types'
import {
  extractCheckoutFieldError,
  validateDireccionEntrega,
  validateFormaPago,
  validateNotas,
  type CheckoutFormValues,
} from '../validation/checkoutValidation'

/**
 * Permite revisar el resumen del carrito, completar dirección, forma de pago y notas,
 * y confirmar el pedido conservando el carrito ante errores HTTP.
 */
export function CheckoutPage() {
  const navigate = useNavigate()
  const formaPagoId = useId()
  const notasId = useId()

  const items = useCartItems()
  const total = useCartTotal()
  const totalItems = useCartCount()
  const { vaciar } = useCartActions()
  const crearPedidoMutation = useCrearPedido()

  const defaultValues: CheckoutFormValues = {
    direccion_entrega: '',
    forma_pago: 'EFECTIVO',
    notas: '',
  }

  const form = useForm({
    defaultValues,
    onSubmit: async ({ value }) => {
      if (items.length === 0) {
        return
      }

      const trimmedNotas = value.notas.trim()
      const payload: PedidoCreate = {
        items: items.map((item) => ({
          producto_id: item.producto_id,
          cantidad: item.cantidad,
        })),
        direccion_entrega: value.direccion_entrega.trim(),
        forma_pago: value.forma_pago,
        notas: trimmedNotas.length > 0 ? trimmedNotas : null,
      }

      try {
        await crearPedidoMutation.mutateAsync(payload)
        vaciar()
        navigate('/mis-pedidos', { replace: true })
      } catch {
        // El error normalizado permanece en `crearPedidoMutation.error`; se conservan carrito y formulario.
      }
    },
  })

  if (items.length === 0) {
    return (
      <section className="mx-auto max-w-3xl space-y-6 py-4">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Finalizar pedido
          </h1>
          <p className="text-sm text-slate-600">
            Necesitás al menos un producto en el carrito para confirmar una compra.
          </p>
        </header>

        <EstadoVacio
          title="Tu carrito está vacío"
          description="No es posible confirmar un pedido sin productos seleccionados."
          actionLabel="Volver al catálogo"
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
            Finalizar pedido
          </h1>
          <p className="text-sm text-slate-600">
            Completá los datos de entrega y pago para confirmar tu compra.
          </p>
        </div>

        <Link
          to="/carrito"
          className="text-sm font-medium text-blue-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded"
        >
          Volver al carrito
        </Link>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1.25fr_1fr]">
        <Card title="Datos de entrega y pago">
          {crearPedidoMutation.error && (
            <div
              role="alert"
              className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm font-medium text-rose-700"
            >
              {crearPedidoMutation.error.message}
            </div>
          )}

          <form.Subscribe
            selector={(state) => [state.canSubmit, state.isSubmitting] as const}
          >
            {([canSubmit, isSubmitting]) => {
              const busy = isSubmitting || crearPedidoMutation.isPending

              return (
                <form
                  noValidate
                  aria-busy={busy}
                  className="space-y-4"
                  onSubmit={(event) => {
                    event.preventDefault()
                    event.stopPropagation()
                    void form.handleSubmit()
                  }}
                >
                  <form.Field
                    name="direccion_entrega"
                    validators={{
                      onChange: ({ value }) => validateDireccionEntrega(value),
                      onSubmit: ({ value }) => validateDireccionEntrega(value),
                    }}
                  >
                    {(field) => {
                      const showError =
                        field.state.meta.isTouched || form.state.submissionAttempts > 0
                      const errorMessage = showError
                        ? extractCheckoutFieldError(field.state.meta.errors)
                        : null

                      return (
                        <Input
                          label="Dirección de entrega"
                          name={field.name}
                          type="text"
                          autoComplete="street-address"
                          placeholder="Ej. Av. Siempre Viva 742, Piso 2"
                          disabled={busy}
                          value={field.state.value}
                          onBlur={field.handleBlur}
                          onChange={(event) => field.handleChange(event.target.value)}
                          error={errorMessage}
                        />
                      )
                    }}
                  </form.Field>

                  <form.Field
                    name="forma_pago"
                    validators={{
                      onChange: ({ value }) => validateFormaPago(value),
                      onSubmit: ({ value }) => validateFormaPago(value),
                    }}
                  >
                    {(field) => {
                      const showError =
                        field.state.meta.isTouched || form.state.submissionAttempts > 0
                      const errorMessage = showError
                        ? extractCheckoutFieldError(field.state.meta.errors)
                        : null
                      const hasError = Boolean(errorMessage)
                      const errorId = hasError ? `${formaPagoId}-error` : undefined

                      return (
                        <div className="space-y-1.5">
                          <label
                            htmlFor={formaPagoId}
                            className="block text-sm font-medium text-slate-700"
                          >
                            Forma de pago
                          </label>
                          <select
                            id={formaPagoId}
                            name={field.name}
                            disabled={busy}
                            value={field.state.value}
                            aria-invalid={hasError || undefined}
                            aria-describedby={errorId}
                            onBlur={field.handleBlur}
                            onChange={(event) =>
                              field.handleChange(event.target.value as FormaPago)
                            }
                            className={`w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500 ${
                              hasError
                                ? 'border-rose-500 focus-visible:ring-rose-500'
                                : 'border-slate-300 focus-visible:ring-blue-600'
                            }`}
                          >
                            <option value="EFECTIVO">Efectivo</option>
                            <option value="TRANSFERENCIA">Transferencia</option>
                          </select>

                          {hasError && (
                            <p
                              id={errorId}
                              role="alert"
                              className="text-xs font-medium text-rose-600"
                            >
                              {errorMessage}
                            </p>
                          )}
                        </div>
                      )
                    }}
                  </form.Field>

                  <form.Field
                    name="notas"
                    validators={{
                      onChange: ({ value }) => validateNotas(value),
                      onSubmit: ({ value }) => validateNotas(value),
                    }}
                  >
                    {(field) => {
                      const showError =
                        field.state.meta.isTouched || form.state.submissionAttempts > 0
                      const errorMessage = showError
                        ? extractCheckoutFieldError(field.state.meta.errors)
                        : null
                      const hasError = Boolean(errorMessage)
                      const errorId = hasError ? `${notasId}-error` : undefined

                      return (
                        <div className="space-y-1.5">
                          <label
                            htmlFor={notasId}
                            className="block text-sm font-medium text-slate-700"
                          >
                            Notas adicionales (opcional)
                          </label>
                          <textarea
                            id={notasId}
                            name={field.name}
                            rows={3}
                            placeholder="Indicaciones para el repartidor o aclaraciones…"
                            disabled={busy}
                            value={field.state.value}
                            aria-invalid={hasError || undefined}
                            aria-describedby={errorId}
                            onBlur={field.handleBlur}
                            onChange={(event) => field.handleChange(event.target.value)}
                            className={`w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500 ${
                              hasError
                                ? 'border-rose-500 focus-visible:ring-rose-500'
                                : 'border-slate-300 focus-visible:ring-blue-600'
                            }`}
                          />

                          {hasError && (
                            <p
                              id={errorId}
                              role="alert"
                              className="text-xs font-medium text-rose-600"
                            >
                              {errorMessage}
                            </p>
                          )}
                        </div>
                      )
                    }}
                  </form.Field>

                  <Button
                    type="submit"
                    variant="primary"
                    className="w-full"
                    disabled={!canSubmit || busy || items.length === 0}
                    isLoading={busy}
                    loadingText="Confirmando pedido…"
                  >
                    Confirmar pedido
                  </Button>
                </form>
              )
            }}
          </form.Subscribe>
        </Card>

        <Card title="Resumen del pedido" className="h-fit">
          <ul className="divide-y divide-slate-100 text-sm">
            {items.map((item) => {
              const subtotal =
                Math.round(item.precio_unitario * item.cantidad * 100) / 100

              return (
                <li
                  key={item.producto_id}
                  className="flex items-start justify-between gap-3 py-3 first:pt-0"
                >
                  <div className="space-y-0.5">
                    <p className="font-medium text-slate-900">{item.nombre}</p>
                    <p className="text-xs text-slate-500">
                      {item.cantidad} × {formatPrecio(item.precio_unitario)}
                    </p>
                  </div>
                  <span className="font-semibold whitespace-nowrap text-slate-900">
                    {formatPrecio(subtotal)}
                  </span>
                </li>
              )
            })}
          </ul>

          <dl className="mt-4 space-y-2 border-t border-slate-200 pt-3 text-sm">
            <div className="flex items-center justify-between text-slate-600">
              <dt>Unidades</dt>
              <dd className="font-medium text-slate-900">{totalItems}</dd>
            </div>
            <div className="flex items-center justify-between text-base font-bold text-slate-900">
              <dt>Total a pagar</dt>
              <dd>{formatPrecio(total)}</dd>
            </div>
          </dl>
        </Card>
      </div>
    </section>
  )
}
