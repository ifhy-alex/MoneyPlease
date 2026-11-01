import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { job, server, skillsGraph, universePoint } from '../test/handlers'
import { media } from '../test/setup'
import { renderWithProviders } from '../test/render'
import { SCALE } from '../universe/stars'
import Universe from './Universe'

// Escena falsa: jsdom no tiene WebGL. Guarda las llamadas y deja simular hover y clic sobre estrellas.
const fake = vi.hoisted(() => ({
  calls: {} as Record<string, unknown[][]>,
  hover: null as null | ((id: string | null, screen: { x: number; y: number }) => void),
  pick: null as null | ((id: string) => void),
  noWebGL: false,
  opts: [] as unknown[],
}))

vi.mock('../universe/scene', () => {
  class NoWebGL extends Error {}
  return {
    NoWebGL,
    webglAvailable: () => !fake.noWebGL,
    createScene: (_el: HTMLElement, opts: unknown) => {
      fake.opts.push(opts)
      if (fake.noWebGL) throw new NoWebGL('sin webgl')
      const rec = (name: string) => (...args: unknown[]) => { (fake.calls[name] ??= []).push(args) }
      return {
        setStars: rec('setStars'), setLinks: rec('setLinks'), setLabels: rec('setLabels'), setCenter: rec('setCenter'),
        highlight: rec('highlight'), flyTo: rec('flyTo'), dispose: rec('dispose'),
        onHover: (cb: typeof fake.hover) => { fake.hover = cb },
        onPick: (cb: typeof fake.pick) => { fake.pick = cb },
      }
    },
  }
})

function reset() {
  fake.calls = {}
  fake.hover = null
  fake.pick = null
  fake.noWebGL = false
  fake.opts = []
}

const last = (name: string) => fake.calls[name]?.at(-1)

function withUniverse() {
  reset()
  server.use(
    http.get('/api/universe', () => HttpResponse.json({
      total: 3,
      puntos: [universePoint(1, 95, 0, { empresa: 'HPE' }), universePoint(2, 70, 1), universePoint(3, null, 1)],
      nubes: [{ id: 0, nombre: 'Java · Python', x: 0.1, y: -0.1, z: 0.05, n: 1 },
        { id: 1, nombre: 'Redes · Linux', x: 0.25, y: -0.25, z: 0.125, n: 2 }],
    })),
    http.get('/api/jobs/1', () => HttpResponse.json({ job: job(1), descripcion_texto: 'x', match: null, etiqueta: null, postulacion: null })),
  )
}

describe('Universo: ofertas', () => {
  it('dibuja una estrella por oferta y nombra las nubes', async () => {
    withUniverse()
    renderWithProviders(<Universe />)
    await waitFor(() => expect((last('setStars')?.[0] as unknown[])?.length).toBe(3))
    const labels = (last('setLabels')?.[0] as { text: string }[]).map((l) => l.text)
    expect(labels).toEqual(['Java · Python · 1', 'Redes · Linux · 2'])
  })

  it('buscar y Enter hace volar la cámara a la oferta', async () => {
    withUniverse()
    renderWithProviders(<Universe />)
    await waitFor(() => expect((last('setStars')?.[0] as unknown[])?.length).toBe(3))
    await userEvent.type(screen.getByRole('searchbox', { name: /buscar/i }), 'Oferta 2{Enter}')
    const [pos] = last('flyTo') as [number[]]
    expect(pos.map((v) => Math.round(v * 1e6) / 1e6)).toEqual([0.2 * SCALE, -0.2 * SCALE, 0.1 * SCALE].map((v) => Math.round(v * 1e6) / 1e6))
  })

  it('el puntaje mínimo apaga las demás estrellas', async () => {
    withUniverse()
    renderWithProviders(<Universe />)
    await waitFor(() => expect((last('setStars')?.[0] as unknown[])?.length).toBe(3))
    fireEvent.change(screen.getByLabelText(/puntaje mínimo/i), { target: { value: '80' } })
    const stars = last('setStars')?.[0] as { id: string; opacity: number }[]
    expect(stars.map((s) => s.opacity)).toEqual([1, 0.12, 0.12])
  })

  it('tocar una estrella abre el detalle', async () => {
    withUniverse()
    renderWithProviders(<Universe />)
    await waitFor(() => expect(fake.pick).toBeTruthy())
    act(() => fake.pick!('o:1'))
    expect(await screen.findByRole('dialog', { name: 'Detalle de la oferta' })).toBeInTheDocument()
  })

  it('pasar sobre una estrella muestra su tooltip', async () => {
    withUniverse()
    renderWithProviders(<Universe />)
    await waitFor(() => expect(fake.hover).toBeTruthy())
    act(() => fake.hover!('o:1', { x: 100, y: 80 }))
    expect(screen.getByRole('tooltip')).toHaveTextContent('Oferta 1')
  })

  it('una nube del panel hace volar la cámara a su centro', async () => {
    withUniverse()
    renderWithProviders(<Universe />)
    const panel = await screen.findByRole('list', { name: /nubes/i })
    await userEvent.click(within(panel).getByRole('button', { name: /redes · linux/i }))
    const [pos] = last('flyTo') as [number[]]
    expect(pos).toEqual([0.25 * SCALE, -0.25 * SCALE, 0.125 * SCALE])
  })

  it('sin WebGL explica y ofrece volver', async () => {
    withUniverse()
    fake.noWebGL = true
    renderWithProviders(<Universe />)
    expect(await screen.findByText(/tu navegador no puede mostrar el universo 3d/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /volver a inicio/i })).toHaveAttribute('href', '/')
  })

  it('con movimiento reducido la escena lo sabe', async () => {
    withUniverse()
    media.reducedMotion = true
    renderWithProviders(<Universe />)
    await waitFor(() => expect(fake.opts.at(-1)).toEqual({ reducedMotion: true }))
  })

  it('al salir libera la escena', async () => {
    withUniverse()
    const { unmount } = renderWithProviders(<Universe />)
    await waitFor(() => expect((last('setStars')?.[0] as unknown[])?.length).toBe(3))
    unmount()
    expect(fake.calls.dispose).toHaveLength(1)
  })

  it('sin perfil invita a ir a Perfil', async () => {
    reset()
    server.use(http.get('/api/universe', () => HttpResponse.json({ detail: 'Todavía no hay perfil guardado' }, { status: 404 })))
    renderWithProviders(<Universe />)
    expect(await screen.findByText(/guarda tu perfil para ver el universo/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /ir a perfil/i })).toHaveAttribute('href', '/perfil')
  })

  it('sin ofertas lo dice', async () => {
    reset()
    renderWithProviders(<Universe />)
    expect(await screen.findByText('Todavía no hay ofertas para mostrar en el universo.')).toBeInTheDocument()
  })
})

describe('Universo: habilidades', () => {
  function withGraph() {
    reset()
    server.use(
      http.get('/api/skills-graph', () => HttpResponse.json(skillsGraph())),
      http.get('/api/jobs/2', () => HttpResponse.json({ job: job(2), descripcion_texto: 'x', match: null, etiqueta: null, postulacion: null })),
    )
  }
  const route = '/universo?vista=habilidades'

  it('dibuja las habilidades con nombre y sus conexiones', async () => {
    withGraph()
    renderWithProviders(<Universe />, { route })
    await waitFor(() => expect((last('setLinks')?.[0] as unknown[])?.length).toBe(3))
    const labels = (last('setLabels')?.[0] as { text: string }[]).map((l) => l.text)
    expect(labels).toEqual(expect.arrayContaining(['Java', 'Docker']))
    expect(last('setCenter')).toEqual([false])
  })

  it('pasar sobre una habilidad resalta sus ofertas', async () => {
    withGraph()
    renderWithProviders(<Universe />, { route })
    await waitFor(() => expect((last('setLinks')?.[0] as unknown[])?.length).toBe(3))
    act(() => fake.hover!('s:Docker', { x: 10, y: 10 }))
    expect(last('highlight')).toEqual([['s:Docker', 'o:1']])
    act(() => fake.hover!(null, { x: 0, y: 0 }))
    expect(last('highlight')).toEqual([null])
  })

  it('tocar una habilidad lista sus ofertas por puntaje', async () => {
    withGraph()
    renderWithProviders(<Universe />, { route })
    await waitFor(() => expect(fake.pick).toBeTruthy())
    act(() => fake.pick!('s:Java'))
    const list = await screen.findByRole('list', { name: /ofertas de java/i })
    expect(within(list).getAllByRole('button').map((b) => b.textContent)).toEqual([
      expect.stringContaining('Oferta 1'), expect.stringContaining('Oferta 2')])
  })

  it('tocar una oferta abre el detalle', async () => {
    withGraph()
    renderWithProviders(<Universe />, { route })
    await waitFor(() => expect(fake.pick).toBeTruthy())
    act(() => fake.pick!('o:2'))
    expect(await screen.findByRole('dialog', { name: 'Detalle de la oferta' })).toBeInTheDocument()
  })

  it('muestra aparte las habilidades sin ofertas', async () => {
    withGraph()
    renderWithProviders(<Universe />, { route })
    expect(await screen.findByText(/sin ofertas que las pidan todavía/i)).toHaveTextContent('Python')
  })
})
