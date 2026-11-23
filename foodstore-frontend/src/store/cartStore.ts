/**
 * Store global del carrito de compras del cliente.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Sección "Estado, datos y sesión — cartStore" (págs. 18 y 20): Zustand + `persist` con
 *   `items`, `agregar`, `quitar`, `cambiarCantidad`, `vaciar` y `total`.
 * - Regla `RN-01` (pág. 5): consolida cantidades por `producto_id` sin duplicar líneas.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { useShallow } from 'zustand/react/shallow'

export const CART_STORAGE_KEY = 'foodstore-cart'

export interface CartItem {
  producto_id: number
  nombre: string
  precio_unitario: number
  cantidad: number
}

export interface CartItemInput {
  producto_id: number
  nombre: string
  precio_unitario: number
  cantidad?: number
}

export interface CartState {
  items: CartItem[]
  agregar: (item: CartItemInput) => void
  quitar: (producto_id: number) => void
  cambiarCantidad: (producto_id: number, cantidad: number) => void
  vaciar: () => void
  total: () => number
  totalItems: () => number
}

/** Calcula el importe total del carrito redondeado a dos decimales. */
export function calcularTotalCarrito(items: readonly CartItem[]): number {
  const sum = items.reduce((acc, item) => acc + item.precio_unitario * item.cantidad, 0)
  return Math.round(sum * 100) / 100
}

/** Calcula la cantidad total de unidades acumuladas en el carrito. */
export function calcularCantidadTotalCarrito(items: readonly CartItem[]): number {
  return items.reduce((acc, item) => acc + item.cantidad, 0)
}

function normalizePositiveQuantity(rawQuantity: number | undefined): number {
  if (rawQuantity === undefined || !Number.isFinite(rawQuantity)) {
    return 1
  }
  return Math.max(1, Math.trunc(rawQuantity))
}

export const useCartStore = create<CartState>()(
  persist<CartState, [], [], Pick<CartState, 'items'>>(
    (set, get) => ({
      items: [],

      agregar(input) {
        const cantidad = normalizePositiveQuantity(input.cantidad)
        set((state) => {
          const exists = state.items.some((item) => item.producto_id === input.producto_id)
          if (exists) {
            return {
              items: state.items.map((item) =>
                item.producto_id === input.producto_id
                  ? {
                      ...item,
                      nombre: input.nombre,
                      precio_unitario: input.precio_unitario,
                      cantidad: item.cantidad + cantidad,
                    }
                  : item,
              ),
            }
          }

          return {
            items: [
              ...state.items,
              {
                producto_id: input.producto_id,
                nombre: input.nombre,
                precio_unitario: input.precio_unitario,
                cantidad,
              },
            ],
          }
        })
      },

      quitar(producto_id) {
        set((state) => ({
          items: state.items.filter((item) => item.producto_id !== producto_id),
        }))
      },

      cambiarCantidad(producto_id, cantidad) {
        if (!Number.isFinite(cantidad) || Math.trunc(cantidad) <= 0) {
          set((state) => ({
            items: state.items.filter((item) => item.producto_id !== producto_id),
          }))
          return
        }

        const normalized = Math.trunc(cantidad)
        set((state) => ({
          items: state.items.map((item) =>
            item.producto_id === producto_id ? { ...item, cantidad: normalized } : item,
          ),
        }))
      },

      vaciar() {
        set({ items: [] })
      },

      total() {
        return calcularTotalCarrito(get().items)
      },

      totalItems() {
        return calcularCantidadTotalCarrito(get().items)
      },
    }),
    {
      name: CART_STORAGE_KEY,
      partialize: (state) => ({ items: state.items }),
    },
  ),
)

/** Selector atómico de líneas del carrito. */
export function useCartItems(): CartItem[] {
  return useCartStore((state) => state.items)
}

/** Selector atómico del total monetario del carrito. */
export function useCartTotal(): number {
  return useCartStore((state) => calcularTotalCarrito(state.items))
}

/** Selector atómico de la cantidad total de unidades en el carrito. */
export function useCartCount(): number {
  return useCartStore((state) => calcularCantidadTotalCarrito(state.items))
}

/** Selector shallow de acciones estables para operar sobre el carrito. */
export function useCartActions() {
  return useCartStore(
    useShallow((state) => ({
      agregar: state.agregar,
      quitar: state.quitar,
      cambiarCantidad: state.cambiarCantidad,
      vaciar: state.vaciar,
    })),
  )
}
