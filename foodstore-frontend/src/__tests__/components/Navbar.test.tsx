// Consigna: docs/consignas_examen_2.md, 4/R4 y 7/HU-P2-03 — Pruebas unitarias y de accesibilidad de Navbar.

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Navbar } from '../../components/Navbar'

describe('Navbar Component', () => {
  it('renderiza landmarks semánticos, identidad y badge de versión', () => {
    render(<Navbar onNuevoProducto={vi.fn()} />)

    // Landmark banner (<header>)
    const banner = screen.getByRole('banner')
    expect(banner).toBeInTheDocument()

    // Landmark navigation con aria-label descriptivo
    const nav = screen.getByRole('navigation', {
      name: 'Navegación principal del catálogo',
    })
    expect(nav).toBeInTheDocument()

    // Identidad visual y versión
    expect(screen.getByText('🍔 Food Store Admin')).toBeInTheDocument()
    expect(screen.getByText('Catálogo v1')).toBeInTheDocument()

    // Botón de nuevo producto con aria-label accesible
    const btnNuevo = screen.getByRole('button', {
      name: 'Crear nuevo producto',
    })
    expect(btnNuevo).toBeInTheDocument()
    expect(btnNuevo).toHaveTextContent('+ Nuevo Producto')
    expect(btnNuevo).toBeEnabled()
  })

  it('invoca el callback onNuevoProducto al hacer clic en el botón', async () => {
    const user = userEvent.setup()
    const onNuevoProductoMock = vi.fn()

    render(<Navbar onNuevoProducto={onNuevoProductoMock} />)

    const btnNuevo = screen.getByRole('button', {
      name: 'Crear nuevo producto',
    })
    await user.click(btnNuevo)

    expect(onNuevoProductoMock).toHaveBeenCalledTimes(1)
  })

  it('permanece deshabilitado y no invoca el callback cuando disabled=true', async () => {
    const user = userEvent.setup()
    const onNuevoProductoMock = vi.fn()

    render(<Navbar onNuevoProducto={onNuevoProductoMock} disabled={true} />)

    const btnNuevo = screen.getByRole('button', {
      name: 'Crear nuevo producto',
    })
    expect(btnNuevo).toBeDisabled()

    await user.click(btnNuevo)
    expect(onNuevoProductoMock).not.toHaveBeenCalled()
  })
})
