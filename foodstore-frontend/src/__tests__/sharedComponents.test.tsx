import { QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { UserPublic } from '@/features/auth'
import { AppRoutes } from '@/routes/AppRouter'
import { axiosInstance } from '@/shared/api/axiosInstance'
import { queryClient } from '@/shared/api/queryClient'
import {
  EstadoError,
  EstadoVacio,
  Paginacion,
  Skeleton,
} from '@/shared/components'
import { BadgeEstado, Button, Card, Input, Modal } from '@/shared/ui'
import { useAuthStore } from '@/store/authStore'
import { useCartStore } from '@/store/cartStore'

const originalAdapter = axiosInstance.defaults.adapter

const USER_CLIENTE: UserPublic = {
  id: 2,
  username: 'cliente1',
  full_name: 'Cliente Uno',
  email: 'cliente1@example.com',
  role: 'user',
  disabled: false,
  created_at: '2026-11-20T12:00:00Z',
}

const USER_ADMIN: UserPublic = {
  id: 1,
  username: 'admin',
  full_name: 'Admin FoodStore',
  email: 'admin@example.com',
  role: 'admin',
  disabled: false,
  created_at: '2026-11-20T12:00:00Z',
}

function createAxiosResponse(
  config: InternalAxiosRequestConfig,
  status: number,
  data: unknown,
): AxiosResponse {
  return {
    data,
    status,
    statusText: String(status),
    headers: {},
    config,
  }
}

beforeEach(() => {
  localStorage.clear()
  queryClient.clear()
  useCartStore.getState().vaciar()
  useAuthStore.setState({ usuario: null, cargando: false, error: null })
  document.body.style.overflow = ''
})

afterEach(() => {
  axiosInstance.defaults.adapter = originalAdapter
  useCartStore.getState().vaciar()
  useAuthStore.setState({ usuario: null, cargando: false, error: null })
  document.body.style.overflow = ''
  localStorage.clear()
  vi.restoreAllMocks()
})

describe('Primitivas shared/ui', () => {
  it('Button y Card renderizan variantes, tipo button por defecto y estado isLoading accesible', () => {
    render(
      <Card
        title="Resumen"
        subtitle="Detalle del pedido"
        headerAction={<span>Acción</span>}
        footer={<span>Pie de tarjeta</span>}
      >
        <Button variant="primary">Guardar</Button>
        <Button variant="danger" isLoading loadingText="Procesando…">
          Eliminar
        </Button>
      </Card>,
    )

    expect(screen.getByRole('heading', { name: 'Resumen' })).toBeInTheDocument()
    expect(screen.getByText('Detalle del pedido')).toBeInTheDocument()
    expect(screen.getByText('Acción')).toBeInTheDocument()
    expect(screen.getByText('Pie de tarjeta')).toBeInTheDocument()

    const saveBtn = screen.getByRole('button', { name: 'Guardar' })
    expect(saveBtn).toHaveAttribute('type', 'button')
    expect(saveBtn).toBeEnabled()

    const loadingBtn = screen.getByRole('button', { name: 'Procesando…' })
    expect(loadingBtn).toBeDisabled()
    expect(loadingBtn).toHaveAttribute('aria-busy', 'true')
  })

  it('Input asocia label, helperText, aria-invalid, aria-describedby y error con role="alert"', () => {
    render(
      <Input
        label="Dirección de entrega"
        helperText="Entre 5 y 200 caracteres"
        error="La dirección es obligatoria"
      />,
    )

    const input = screen.getByLabelText('Dirección de entrega')
    expect(input).toHaveAttribute('aria-invalid', 'true')

    const describedBy = input.getAttribute('aria-describedby')
    expect(describedBy).toBeTruthy()

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('La dirección es obligatoria')
    expect(describedBy).toContain(alert.id)

    const helper = screen.getByText('Entre 5 y 200 caracteres')
    expect(describedBy).toContain(helper.id)
  })

  it('Modal expone atributos ARIA, bloquea/restaura body overflow y cierra con Escape/backdrop solo cuando no está busy', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()

    const { rerender, unmount } = render(
      <Modal isOpen={false} onClose={onClose} title="Editar categoría">
        <p>Contenido</p>
      </Modal>,
    )

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(document.body.style.overflow).toBe('')

    rerender(
      <Modal isOpen={true} onClose={onClose} title="Editar categoría">
        <p>Contenido</p>
      </Modal>,
    )

    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    const titleEl = screen.getByRole('heading', { name: 'Editar categoría' })
    expect(dialog).toHaveAttribute('aria-labelledby', titleEl.id)
    expect(document.body.style.overflow).toBe('hidden')

    // Clic dentro del diálogo no cierra
    await user.click(screen.getByText('Contenido'))
    expect(onClose).not.toHaveBeenCalled()

    // Clic en backdrop y Escape cierran cuando no está ocupado
    await user.click(screen.getByTestId('modal-backdrop'))
    expect(onClose).toHaveBeenCalledTimes(1)

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(2)

    // Con isSubmitting/busy bloquea Escape, backdrop y botón cerrar
    rerender(
      <Modal isOpen={true} onClose={onClose} title="Editar categoría" isSubmitting={true}>
        <p>Contenido</p>
      </Modal>,
    )

    expect(screen.getByRole('dialog')).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByRole('button', { name: 'Cerrar modal' })).toBeDisabled()

    await user.click(screen.getByTestId('modal-backdrop'))
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(2)

    // Restaura overflow al cerrar / desmontar
    rerender(
      <Modal isOpen={false} onClose={onClose} title="Editar categoría">
        <p>Contenido</p>
      </Modal>,
    )
    expect(document.body.style.overflow).toBe('')

    rerender(
      <Modal isOpen={true} onClose={onClose} title="Editar categoría">
        <p>Contenido</p>
      </Modal>,
    )
    expect(document.body.style.overflow).toBe('hidden')
    unmount()
    expect(document.body.style.overflow).toBe('')
  })

  it('BadgeEstado diferencia los cuatro estados del pedido con texto y estilos semánticos', () => {
    render(
      <div>
        <BadgeEstado estado="PENDIENTE" />
        <BadgeEstado estado="EN_PREPARACION" />
        <BadgeEstado estado="ENTREGADO" />
        <BadgeEstado estado="CANCELADO" />
      </div>,
    )

    expect(screen.getByText('Pendiente')).toHaveClass('bg-amber-100', 'text-amber-800')
    expect(screen.getByText('En preparación')).toHaveClass('bg-blue-100', 'text-blue-800')
    expect(screen.getByText('Entregado')).toHaveClass('bg-emerald-100', 'text-emerald-800')
    expect(screen.getByText('Cancelado')).toHaveClass('bg-rose-100', 'text-rose-800')
  })
})

describe('Componentes shared/components', () => {
  it('Paginacion calcula páginas, marca aria-current="page", deshabilita extremos y emite nuevo skip', async () => {
    const user = userEvent.setup()
    const onPageChange = vi.fn()

    const { rerender } = render(
      <Paginacion skip={0} limit={10} total={25} onPageChange={onPageChange} />,
    )

    expect(screen.getByRole('navigation', { name: 'Paginación' })).toBeInTheDocument()
    const activePage = screen.getByText('Página 1 de 3')
    expect(activePage).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeEnabled()

    await user.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(onPageChange).toHaveBeenCalledWith(10)

    rerender(<Paginacion skip={20} limit={10} total={25} onPageChange={onPageChange} />)
    expect(screen.getByText('Página 3 de 3')).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled()

    await user.click(screen.getByRole('button', { name: 'Anterior' }))
    expect(onPageChange).toHaveBeenLastCalledWith(10)
  })

  it('Skeleton, EstadoVacio y EstadoError exponen roles accesibles y variante inline-refetch no destructiva', async () => {
    const user = userEvent.setup()
    const onEmptyAction = vi.fn()
    const onRetry = vi.fn()

    const { container } = render(
      <div>
        <Skeleton count={2} label="Cargando productos…" />
        <EstadoVacio
          title="Sin productos"
          description="No encontramos coincidencias."
          actionLabel="Limpiar filtros"
          onAction={onEmptyAction}
        />
        <EstadoError
          message="No se pudo conectar con el servidor"
          onRetry={onRetry}
        />
        <section aria-label="Listado con datos previos">
          <EstadoError
            variant="inline-refetch"
            message="Tiempo de espera agotado al refrescar"
            onRetry={onRetry}
          />
          <p>Pizza Muzzarella</p>
        </section>
      </div>,
    )

    const statuses = screen.getAllByRole('status')
    const skeletonStatus = statuses.find((el) => el.getAttribute('aria-busy') === 'true')
    expect(skeletonStatus).toBeDefined()
    expect(skeletonStatus).toHaveTextContent('Cargando productos…')
    expect(container.querySelector('.motion-reduce\\:animate-none')).not.toBeNull()
    expect(container.querySelectorAll('[aria-hidden="true"]').length).toBeGreaterThan(0)

    await user.click(screen.getByRole('button', { name: 'Limpiar filtros' }))
    expect(onEmptyAction).toHaveBeenCalledTimes(1)

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('No se pudo conectar con el servidor')

    const refetchStatus = statuses.find((el) =>
      el.textContent?.includes('Tiempo de espera agotado al refrescar'),
    )
    expect(refetchStatus).toBeDefined()
    expect(screen.getByText('Pizza Muzzarella')).toBeInTheDocument()

    const retryButtons = screen.getAllByRole('button', { name: 'Reintentar' })
    await user.click(retryButtons[0])
    await user.click(retryButtons[1])
    expect(onRetry).toHaveBeenCalledTimes(2)
  })
})

describe('Layout Navbar y MainLayout integrados en AppRoutes', () => {
  it('muestra enlaces públicos, badge reactivo del carrito e inicio/registro sin sesión', () => {
    useCartStore.getState().agregar({
      producto_id: 1,
      nombre: 'Pizza Muzzarella',
      precio_unitario: 5000,
      cantidad: 2,
    })

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/']}>
          <AppRoutes />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(screen.getByRole('link', { name: 'Food Store' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Catálogo' })).toBeInTheDocument()
    expect(screen.getByTestId('cart-badge')).toHaveTextContent('2')
    expect(screen.getByRole('link', { name: 'Iniciar sesión' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Registrarse' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Mis pedidos' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Usuarios' })).not.toBeInTheDocument()
    expect(screen.getAllByRole('main')).toHaveLength(1)
  })

  it('oculta enlaces admin para rol user y los muestra junto a nombre/rol para admin', () => {
    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })

    const { rerender } = render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/']}>
          <AppRoutes />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(screen.getByText('Cliente Uno')).toBeInTheDocument()
    expect(screen.getByText('Cliente')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Mis pedidos' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Resumen' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Usuarios' })).not.toBeInTheDocument()

    useAuthStore.setState({ usuario: USER_ADMIN, cargando: false, error: null })
    rerender(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/']}>
          <AppRoutes />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(screen.getByText('Admin FoodStore')).toBeInTheDocument()
    expect(screen.getByText('Admin')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Resumen' })).toHaveAttribute('href', '/admin/resumen')
    expect(screen.getByRole('link', { name: 'Categorías' })).toHaveAttribute(
      'href',
      '/admin/categorias',
    )
    expect(screen.getByRole('link', { name: 'Productos' })).toHaveAttribute(
      'href',
      '/admin/productos',
    )
    expect(screen.getByRole('link', { name: 'Pedidos' })).toHaveAttribute('href', '/admin/pedidos')
    expect(screen.getByRole('link', { name: 'Usuarios' })).toHaveAttribute(
      'href',
      '/admin/usuarios',
    )
  })

  it('Cerrar sesión en Navbar invoca logout, limpia sesión y redirige a /login', async () => {
    const user = userEvent.setup()
    let logoutCalls = 0
    const mockAdapter: AxiosAdapter = async (config) => {
      if (config.url === '/auth/logout') {
        logoutCalls += 1
        return createAxiosResponse(config, 200, { message: 'Logout exitoso' })
      }
      if (config.url === '/categorias') {
        return createAxiosResponse(config, 200, [])
      }
      if (config.url === '/productos') {
        return createAxiosResponse(config, 200, { total: 0, items: [] })
      }
      throw new Error(`Unexpected URL: ${config.url}`)
    }
    axiosInstance.defaults.adapter = mockAdapter

    useAuthStore.setState({ usuario: USER_CLIENTE, cargando: false, error: null })

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/']}>
          <AppRoutes />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }))

    await waitFor(() => {
      expect(logoutCalls).toBe(1)
      expect(useAuthStore.getState().usuario).toBeNull()
      expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    })
  })
})
