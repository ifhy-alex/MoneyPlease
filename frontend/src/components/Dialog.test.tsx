import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { Dialog } from './Dialog'

function Harness() {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>Abrir</button>
      {open && (
        <Dialog title="Prueba" onClose={() => setOpen(false)}>
          <button type="button">Primero</button>
          <button type="button" onClick={() => setOpen(false)}>Último</button>
        </Dialog>
      )}
    </>
  )
}

describe('Dialog', () => {
  it('es modal y tiene nombre', () => {
    render(<Dialog title="Prueba" onClose={() => {}}><button type="button">Ok</button></Dialog>)
    const dialog = screen.getByRole('dialog', { name: 'Prueba' })
    expect(dialog).toHaveAttribute('aria-modal', 'true')
  })

  it('cierra con Escape', async () => {
    const onClose = vi.fn()
    render(<Dialog title="Prueba" onClose={onClose}><button type="button">Ok</button></Dialog>)
    await userEvent.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('enfoca el primer elemento al abrir', async () => {
    render(<Harness />)
    await userEvent.click(screen.getByRole('button', { name: 'Abrir' }))
    expect(screen.getByRole('button', { name: 'Primero' })).toHaveFocus()
  })

  it('Tab desde el último vuelve al primero y Shift+Tab al revés', async () => {
    render(<Harness />)
    await userEvent.click(screen.getByRole('button', { name: 'Abrir' }))
    await userEvent.tab()
    expect(screen.getByRole('button', { name: 'Último' })).toHaveFocus()
    await userEvent.tab()
    expect(screen.getByRole('button', { name: 'Primero' })).toHaveFocus()
    await userEvent.tab({ shift: true })
    expect(screen.getByRole('button', { name: 'Último' })).toHaveFocus()
  })

  it('devuelve el foco al cerrar', async () => {
    render(<Harness />)
    const opener = screen.getByRole('button', { name: 'Abrir' })
    await userEvent.click(opener)
    await userEvent.click(screen.getByRole('button', { name: 'Último' }))
    expect(opener).toHaveFocus()
  })
})
