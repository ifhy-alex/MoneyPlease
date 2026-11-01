import { act, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { media } from '../test/setup'
import AmbientField from './AmbientField'
import { EmptyState } from './EmptyState'
import { Grain } from './Grain'

describe('decoración', () => {
  it.each(['sin-ofertas', 'sin-postulaciones', 'sin-perfil'] as const)('EmptyState %s tiene patrón y texto', (kind) => {
    const { container } = render(<EmptyState kind={kind} title="Título" text="Texto" />)
    expect(screen.getByText('Título')).toBeInTheDocument()
    expect(container.querySelector('svg[aria-hidden="true"]')).not.toBeNull()
  })

  it('el patrón vacío es determinista', () => {
    const a = render(<EmptyState kind="sin-perfil" title="A" />).container.querySelector('svg')!.innerHTML
    const b = render(<EmptyState kind="sin-perfil" title="B" />).container.querySelector('svg')!.innerHTML
    expect(a).toBe(b)
  })

  it('el fondo no se puede enfocar ni tapa clics', () => {
    const { container } = render(<><AmbientField /><Grain /></>)
    for (const el of Array.from(container.children)) {
      expect(el).toHaveAttribute('aria-hidden', 'true')
      expect(el.getAttribute('class')).toContain('pointer-events-none')
    }
  })

  it('con movimiento reducido el campo dibuja un solo cuadro', () => {
    media.reducedMotion = true
    const raf = vi.spyOn(window, 'requestAnimationFrame')
    render(<AmbientField />)
    expect(raf.mock.calls.length).toBeLessThanOrEqual(1)
    raf.mockRestore()
  })

  it('sin movimiento reducido el campo anima', () => {
    const raf = vi.spyOn(window, 'requestAnimationFrame').mockImplementation(() => 1)
    render(<AmbientField />)
    expect(raf).toHaveBeenCalled()
    raf.mockRestore()
  })

  it('con la pestaña oculta no programa más cuadros', () => {
    const callbacks: FrameRequestCallback[] = []
    const raf = vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => { callbacks.push(cb); return callbacks.length })
    const hidden = vi.spyOn(document, 'hidden', 'get').mockReturnValue(true)
    render(<AmbientField />)
    act(() => { document.dispatchEvent(new Event('visibilitychange')) })
    const before = raf.mock.calls.length
    act(() => { callbacks.at(-1)?.(1000) })
    expect(raf.mock.calls.length).toBe(before)
    hidden.mockRestore()
    raf.mockRestore()
  })
})
