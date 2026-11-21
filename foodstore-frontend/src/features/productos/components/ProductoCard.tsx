/**
 * Tarjeta de producto del catálogo público con validación segura de imagen y acceso al carrito.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - HU-TPI-02 (págs. 12–14, 18–20): presentación de producto, stock/disponibilidad y `cartStore`.
 */
import { useState } from 'react'

import { Button, Card } from '@/shared/ui'
import { useCartStore } from '@/store/cartStore'

import type { ProductoRead } from '../types/producto.types'

export interface ProductoCardProps {
  producto: ProductoRead
}

const ARS_FORMATTER = new Intl.NumberFormat('es-AR', {
  style: 'currency',
  currency: 'ARS',
  minimumFractionDigits: 2,
})

/** Valida que `imagen_url` use un esquema seguro (`https://`, `http://` o `/img/`). */
export function isValidImageUrl(url: string | null | undefined): url is string {
  if (typeof url !== 'string') {
    return false
  }
  const trimmed = url.trim()
  if (!trimmed || trimmed.startsWith('//')) {
    return false
  }
  if (trimmed.startsWith('https://') || trimmed.startsWith('http://')) {
    return true
  }
  if (trimmed.startsWith('/img/') && !trimmed.includes('..')) {
    return true
  }
  return false
}

/** Formatea un precio numérico en pesos argentinos (`ARS`). */
export function formatPrecio(precio: number): string {
  return ARS_FORMATTER.format(precio)
}

/** Tarjeta accesible de producto con fallback de imagen sin reintentos en bucle. */
export function ProductoCard({ producto }: ProductoCardProps) {
  const agregar = useCartStore((state) => state.agregar)
  const [failedUrl, setFailedUrl] = useState<string | null>(null)

  const normalizedUrl = producto.imagen_url?.trim() ?? null
  const showImage = isValidImageUrl(normalizedUrl) && failedUrl !== normalizedUrl
  const sinStock = !producto.disponible || producto.stock <= 0

  return (
    <Card as="article" className="flex h-full flex-col justify-between overflow-hidden">
      <div className="space-y-3">
        <div className="relative h-44 w-full overflow-hidden rounded-lg bg-slate-100">
          {showImage ? (
            <img
              src={normalizedUrl}
              alt={producto.nombre}
              loading="lazy"
              onError={() => setFailedUrl(normalizedUrl)}
              className="h-44 w-full rounded-lg bg-slate-100 object-cover"
            />
          ) : (
            <div className="flex h-full w-full flex-col items-center justify-center gap-1.5 text-slate-400">
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                className="h-10 w-10"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Zm10.5-11.25h.008v.008h-.008V8.25Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z"
                />
              </svg>
              <span className="text-xs font-medium text-slate-500">Imagen no disponible</span>
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
            {producto.categoria?.nombre ?? 'Sin categoría'}
          </span>
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
              sinStock ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800'
            }`}
          >
            {sinStock ? 'Sin stock' : `Stock: ${producto.stock}`}
          </span>
        </div>

        <div className="space-y-1">
          <h2 className="text-base font-semibold text-slate-900">{producto.nombre}</h2>
          {producto.descripcion && (
            <p className="line-clamp-2 text-sm text-slate-600">{producto.descripcion}</p>
          )}
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between gap-3 border-t border-slate-100 pt-3">
        <span className="text-base font-bold text-slate-900">
          {formatPrecio(producto.precio_base)}
        </span>
        <Button
          variant="primary"
          size="sm"
          disabled={sinStock}
          onClick={() =>
            agregar({
              producto_id: producto.id,
              nombre: producto.nombre,
              precio_unitario: producto.precio_base,
              cantidad: 1,
            })
          }
          aria-label={`Agregar ${producto.nombre} al carrito`}
        >
          Agregar al carrito
        </Button>
      </div>
    </Card>
  )
}
