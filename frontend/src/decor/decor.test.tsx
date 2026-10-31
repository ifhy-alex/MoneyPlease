import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import FlowField from '../art/FlowField'
import { media } from '../test/setup'
import { EmptyState } from './EmptyState'
import { Grain } from './Grain'
import { NightGradient } from './NightGradient'

describe('decoración', () => {
  it.each(['sin-ofertas', 'sin-postulaciones', 'sin-perfil'] as const)('EmptyState %s tiene ilustración y texto', (kind) => {
    const { container } = render(<EmptyState kind={kind} title="Título" text="Texto" />)
    expect(screen.getByText('Título')).toBeInTheDocument()
    expect(container.querySelector('svg[aria-hidden="true"]')).not.toBeNull()
  })

  it('el fondo no se puede enfocar ni tapa clics', () => {
    const { container } = render(<><NightGradient /><Grain /></>)
    for (const el of Array.from(container.children)) {
      expect(el).toHaveAttribute('aria-hidden', 'true')
      expect(el.getAttribute('class')).toContain('pointer-events-none')
    }
  })

  it('con movimiento reducido el flow field dibuja un solo cuadro', () => {
    media.reducedMotion = true
    const raf = vi.spyOn(window, 'requestAnimationFrame')
    render(<FlowField />)
    expect(raf.mock.calls.length).toBeLessThanOrEqual(1)
    raf.mockRestore()
  })

  it('sin movimiento reducido el flow field anima', () => {
    const raf = vi.spyOn(window, 'requestAnimationFrame').mockImplementation(() => 1)
    render(<FlowField />)
    expect(raf).toHaveBeenCalled()
    raf.mockRestore()
  })
})
