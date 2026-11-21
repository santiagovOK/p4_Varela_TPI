import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import {
  CART_STORAGE_KEY,
  useCartActions,
  useCartCount,
  useCartItems,
  useCartStore,
  useCartTotal,
} from '@/store/cartStore'

function CartConsumerHarness() {
  const items = useCartItems()
  const total = useCartTotal()
  const count = useCartCount()
  const { agregar, quitar, cambiarCantidad, vaciar } = useCartActions()

  return (
    <div>
      <p data-testid="count">{count}</p>
      <p data-testid="total">{total}</p>
      <ul data-testid="items">
        {items.map((item) => (
          <li key={item.producto_id}>
            {item.nombre}:{item.cantidad}
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={() =>
          agregar({
            producto_id: 10,
            nombre: 'Hamburguesa Clásica',
            precio_unitario: 4500.5,
          })
        }
      >
        Agregar hamburguesa
      </button>
      <button type="button" onClick={() => cambiarCantidad(10, 3)}>
        Fijar 3
      </button>
      <button type="button" onClick={() => quitar(10)}>
        Quitar hamburguesa
      </button>
      <button type="button" onClick={() => vaciar()}>
        Vaciar carrito
      </button>
    </div>
  )
}

beforeEach(() => {
  localStorage.clear()
  useCartStore.getState().vaciar()
})

afterEach(() => {
  useCartStore.getState().vaciar()
  localStorage.clear()
})

describe('cartStore', () => {
  it('agrega productos nuevos y acumula cantidad sin duplicar líneas para un mismo producto_id', () => {
    const store = useCartStore.getState()

    store.agregar({
      producto_id: 1,
      nombre: 'Pizza Muzzarella',
      precio_unitario: 6000,
    })
    store.agregar({
      producto_id: 1,
      nombre: 'Pizza Muzzarella',
      precio_unitario: 6000,
      cantidad: 2,
    })
    store.agregar({
      producto_id: 2,
      nombre: 'Gaseosa Cola 500ml',
      precio_unitario: 1500.25,
      cantidad: 2,
    })

    const { items, total, totalItems } = useCartStore.getState()
    expect(items).toHaveLength(2)
    expect(items[0]).toEqual({
      producto_id: 1,
      nombre: 'Pizza Muzzarella',
      precio_unitario: 6000,
      cantidad: 3,
    })
    expect(items[1]).toEqual({
      producto_id: 2,
      nombre: 'Gaseosa Cola 500ml',
      precio_unitario: 1500.25,
      cantidad: 2,
    })
    expect(totalItems()).toBe(5)
    expect(total()).toBe(21000.5)
  })

  it('actualiza cantidades, elimina el ítem si cantidad <= 0, quita y vacía el carrito', () => {
    const store = useCartStore.getState()

    store.agregar({
      producto_id: 3,
      nombre: 'Empanada de Carne',
      precio_unitario: 1200.33,
      cantidad: 2,
    })
    store.agregar({
      producto_id: 4,
      nombre: 'Agua Mineral 500ml',
      precio_unitario: 900,
      cantidad: 1,
    })

    store.cambiarCantidad(3, 4)
    expect(useCartStore.getState().items.find((i) => i.producto_id === 3)?.cantidad).toBe(4)
    expect(useCartStore.getState().total()).toBe(5701.32)

    store.cambiarCantidad(3, 0)
    expect(useCartStore.getState().items).toHaveLength(1)
    expect(useCartStore.getState().items[0].producto_id).toBe(4)

    store.agregar({
      producto_id: 5,
      nombre: 'Empanada JyQ',
      precio_unitario: 1100,
      cantidad: 1,
    })
    store.cambiarCantidad(4, -2)
    expect(useCartStore.getState().items).toHaveLength(1)
    expect(useCartStore.getState().items[0].producto_id).toBe(5)

    store.quitar(5)
    expect(useCartStore.getState().items).toHaveLength(0)

    store.agregar({
      producto_id: 6,
      nombre: 'Pizza Napolitana',
      precio_unitario: 7000,
    })
    store.vaciar()
    expect(useCartStore.getState().items).toEqual([])
    expect(useCartStore.getState().total()).toBe(0)
  })

  it('persiste únicamente { items } en localStorage bajo la clave foodstore-cart (partialize)', () => {
    useCartStore.getState().agregar({
      producto_id: 7,
      nombre: 'Hamburguesa Doble Bacon',
      precio_unitario: 5500,
      cantidad: 2,
    })

    const raw = localStorage.getItem(CART_STORAGE_KEY)
    expect(raw).not.toBeNull()

    const parsed = JSON.parse(raw!) as { state: Record<string, unknown>; version: number }
    expect(Object.keys(parsed.state)).toEqual(['items'])
    expect(parsed.state.items).toEqual([
      {
        producto_id: 7,
        nombre: 'Hamburguesa Doble Bacon',
        precio_unitario: 5500,
        cantidad: 2,
      },
    ])
  })

  it('funciona reactivamente con selectores atómicos y useShallow en componentes React', async () => {
    const user = userEvent.setup()
    render(<CartConsumerHarness />)

    expect(screen.getByTestId('count')).toHaveTextContent('0')
    expect(screen.getByTestId('total')).toHaveTextContent('0')

    await user.click(screen.getByRole('button', { name: 'Agregar hamburguesa' }))
    expect(screen.getByTestId('count')).toHaveTextContent('1')
    expect(screen.getByTestId('total')).toHaveTextContent('4500.5')
    expect(screen.getByTestId('items')).toHaveTextContent('Hamburguesa Clásica:1')

    await user.click(screen.getByRole('button', { name: 'Fijar 3' }))
    expect(screen.getByTestId('count')).toHaveTextContent('3')
    expect(screen.getByTestId('total')).toHaveTextContent('13501.5')

    await user.click(screen.getByRole('button', { name: 'Quitar hamburguesa' }))
    expect(screen.getByTestId('count')).toHaveTextContent('0')

    await user.click(screen.getByRole('button', { name: 'Agregar hamburguesa' }))
    await user.click(screen.getByRole('button', { name: 'Vaciar carrito' }))
    expect(screen.getByTestId('count')).toHaveTextContent('0')
    expect(screen.getByTestId('total')).toHaveTextContent('0')
  })
})
