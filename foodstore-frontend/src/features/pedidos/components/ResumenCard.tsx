/**
 * Tarjeta semántica de indicador para el resumen administrativo de pedidos.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Historia `HU-TPI-05` y ruta `/admin/resumen` (págs. 14, 18–20).
 */
import { Card } from '@/shared/ui'

export type ResumenCardTone = 'neutral' | 'amber' | 'blue' | 'emerald' | 'rose' | 'indigo'

export interface ResumenCardProps {
  label: string
  value: string | number
  description?: string
  tone?: ResumenCardTone
  testId?: string
}

const TONE_BADGE_CLASSES: Record<ResumenCardTone, string> = {
  neutral: 'border-slate-200 bg-slate-100 text-slate-700',
  amber: 'border-amber-200 bg-amber-50 text-amber-800',
  blue: 'border-blue-200 bg-blue-50 text-blue-800',
  emerald: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  rose: 'border-rose-200 bg-rose-50 text-rose-800',
  indigo: 'border-indigo-200 bg-indigo-50 text-indigo-800',
}

const TONE_ACCENT_CLASSES: Record<ResumenCardTone, string> = {
  neutral: 'border-l-4 border-l-slate-400',
  amber: 'border-l-4 border-l-amber-500',
  blue: 'border-l-4 border-l-blue-500',
  emerald: 'border-l-4 border-l-emerald-500',
  rose: 'border-l-4 border-l-rose-500',
  indigo: 'border-l-4 border-l-indigo-500',
}

/** Tarjeta accesible de métrica administrativa con etiqueta textual y valor destacado. */
export function ResumenCard({
  label,
  value,
  description,
  tone = 'neutral',
  testId,
}: ResumenCardProps) {
  return (
    <Card
      as="article"
      data-testid={testId}
      className={TONE_ACCENT_CLASSES[tone]}
    >
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-medium text-slate-600">{label}</h2>
          <span
            className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${TONE_BADGE_CLASSES[tone]}`}
          >
            Indicador
          </span>
        </div>

        <p className="text-2xl font-bold tracking-tight text-slate-900">{value}</p>

        {description && <p className="text-xs text-slate-500">{description}</p>}
      </div>
    </Card>
  )
}
