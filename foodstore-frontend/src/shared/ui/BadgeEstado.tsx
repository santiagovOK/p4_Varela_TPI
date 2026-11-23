/**
 * Insignia visual y textual para los cuatro estados normativos de un pedido.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Tabla "Componentes compartidos — shared/ui/" (pág. 18): `BadgeEstado` colorea los cuatro estados.
 * - Máquina de estados `RN-02` (pág. 5): `PENDIENTE`, `EN_PREPARACION`, `ENTREGADO`, `CANCELADO`.
 */
import type { EstadoPedido } from '@/features/pedidos'

export interface BadgeEstadoProps {
  estado: EstadoPedido
  className?: string
}

const ESTADO_CONFIG: Record<EstadoPedido, { label: string; classes: string }> = {
  PENDIENTE: {
    label: 'Pendiente',
    classes: 'bg-amber-100 text-amber-800 border-amber-300',
  },
  EN_PREPARACION: {
    label: 'En preparación',
    classes: 'bg-blue-100 text-blue-800 border-blue-300',
  },
  ENTREGADO: {
    label: 'Entregado',
    classes: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  },
  CANCELADO: {
    label: 'Cancelado',
    classes: 'bg-rose-100 text-rose-800 border-rose-300',
  },
}

/** Muestra el estado del pedido combinando etiqueta legible e identidad cromática. */
export function BadgeEstado({ estado, className = '' }: BadgeEstadoProps) {
  const config = ESTADO_CONFIG[estado]

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${config.classes} ${className}`.trim()}
    >
      {config.label}
    </span>
  )
}
