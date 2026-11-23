/**
 * Página administrativa `/admin/resumen` con tarjetas de indicadores de pedidos.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Historia `HU-TPI-05`, ruta `/admin/resumen` y tabla "Rutas y pantallas" (págs. 14, 18–20).
 */
import { formatPrecio } from '@/features/productos'
import { EstadoError, Skeleton } from '@/shared/components'
import { Button } from '@/shared/ui'

import { ResumenCard, type ResumenCardTone } from '../components/ResumenCard'
import { useResumenPedidos } from '../hooks/useResumenPedidos'
import type { ResumenPedidos } from '../types/pedido.types'

interface IndicadorConfig {
  key: keyof ResumenPedidos
  label: string
  description: string
  tone: ResumenCardTone
  formatValue: (resumen: ResumenPedidos) => string | number
}

const INDICADORES: ReadonlyArray<IndicadorConfig> = [
  {
    key: 'pendientes',
    label: 'Pedidos pendientes',
    description: 'Pedidos aguardando preparación',
    tone: 'amber',
    formatValue: (resumen) => resumen.pendientes,
  },
  {
    key: 'en_preparacion',
    label: 'En preparación',
    description: 'Pedidos actualmente en cocina o armado',
    tone: 'blue',
    formatValue: (resumen) => resumen.en_preparacion,
  },
  {
    key: 'entregados',
    label: 'Pedidos entregados',
    description: 'Pedidos completados con entrega confirmada',
    tone: 'emerald',
    formatValue: (resumen) => resumen.entregados,
  },
  {
    key: 'cancelados',
    label: 'Pedidos cancelados',
    description: 'Pedidos anulados con stock restituido',
    tone: 'rose',
    formatValue: (resumen) => resumen.cancelados,
  },
  {
    key: 'pedidos_hoy',
    label: 'Pedidos de hoy',
    description: 'Total de pedidos registrados en la fecha actual',
    tone: 'indigo',
    formatValue: (resumen) => resumen.pedidos_hoy,
  },
  {
    key: 'ingresos_entregados',
    label: 'Ingresos entregados',
    description: 'Facturación acumulada de pedidos entregados',
    tone: 'emerald',
    formatValue: (resumen) => formatPrecio(resumen.ingresos_entregados),
  },
]

/** Panel administrativo con indicadores agregados de pedidos (`GET /pedidos/resumen`). */
export function AdminResumenPage() {
  const { data, isLoading, isFetching, isError, isRefetchError, error, refetch } =
    useResumenPedidos()

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Resumen administrativo
          </h1>
          <p className="text-sm text-slate-600">
            Indicadores operativos de pedidos e ingresos de pedidos entregados.
          </p>
        </div>

        <Button
          variant="secondary"
          isLoading={isFetching && !isLoading}
          loadingText="Actualizando…"
          disabled={isLoading || isFetching}
          onClick={() => void refetch()}
        >
          Actualizar
        </Button>
      </header>

      {isLoading && !data ? (
        <Skeleton variant="card" count={6} label="Cargando resumen de pedidos…" />
      ) : isError && !data ? (
        <EstadoError
          variant="alert"
          title="No se pudo cargar el resumen de pedidos"
          message={error?.message ?? 'Error al consultar los indicadores de pedidos.'}
          onRetry={() => void refetch()}
        />
      ) : data ? (
        <div className="space-y-5">
          {(isError || isRefetchError) && (
            <EstadoError
              variant="inline-refetch"
              title="No se pudo actualizar el resumen; se conservan los últimos valores confirmados."
              message={error?.message ?? 'Error al actualizar los indicadores de pedidos.'}
              onRetry={() => void refetch()}
            />
          )}

          <div
            className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
            aria-label="Indicadores de pedidos"
          >
            {INDICADORES.map((indicador) => (
              <ResumenCard
                key={indicador.key}
                testId={`resumen-card-${indicador.key}`}
                label={indicador.label}
                value={indicador.formatValue(data)}
                description={indicador.description}
                tone={indicador.tone}
              />
            ))}
          </div>
        </div>
      ) : null}
    </section>
  )
}
