import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { application, insights, job, mapPoint, server } from '../test/handlers'
import { media } from '../test/setup'
import { renderWithProviders } from '../test/render'
import Home from './Home'

function trackFeedback() {
  const calls: unknown[] = []
  server.use(http.post('/api/jobs/:id/feedback', async ({ request }) => {
    calls.push(await request.json())
    return new HttpResponse(null, { status: 204 })
  }))
  return calls
}

describe('Inicio', () => {
  it('muestra el top con fortalezas y brechas', async () => {
    renderWithProviders(<Home />)
    expect(await screen.findByText('Oferta 1')).toBeInTheDocument()
    expect(screen.getByText('Oferta 2')).toBeInTheDocument()
    expect(screen.getAllByText('Java').length).toBeGreaterThan(0)
    expect(screen.getByText(/kubernetes/i)).toBeInTheDocument()
    expect(screen.getByText(/2\/10/)).toBeInTheDocument()
  })

  it('no me interesa oculta la tarjeta y deshacer la devuelve', async () => {
    const calls = trackFeedback()
    renderWithProviders(<Home />)
    const card = (await screen.findByText('Oferta 1')).closest('article')!
    await userEvent.click(within(card).getByRole('button', { name: /no me interesa/i }))
    await waitFor(() => expect(screen.queryByText('Oferta 1')).not.toBeInTheDocument())
    await userEvent.click(await screen.findByRole('button', { name: /deshacer/i }))
    expect(await screen.findByText('Oferta 1')).toBeInTheDocument()
    await waitFor(() => expect(calls).toEqual([{ valor: 'no_interesa' }, { valor: null }]))
  })

  it('si el feedback falla, la tarjeta vuelve y avisa', async () => {
    server.use(http.post('/api/jobs/:id/feedback', () => HttpResponse.json({ detail: 'La oferta no existe' }, { status: 404 })))
    renderWithProviders(<Home />)
    const card = (await screen.findByText('Oferta 1')).closest('article')!
    await userEvent.click(within(card).getByRole('button', { name: /no me interesa/i }))
    expect(await screen.findByText('La oferta no existe')).toBeInTheDocument()
    expect(await screen.findByText('Oferta 1')).toBeInTheDocument()
  })

  it('guardar crea la postulación y un 409 no es error', async () => {
    let posts = 0
    server.use(http.post('/api/applications', () => {
      posts += 1
      return HttpResponse.json({ detail: 'ya está' }, { status: 409 })
    }))
    renderWithProviders(<Home />)
    const card = (await screen.findByText('Oferta 1')).closest('article')!
    await userEvent.click(within(card).getByRole('button', { name: /guardar/i }))
    await waitFor(() => expect(posts).toBe(1))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('sin ofertas muestra el estado vacío con enlace al perfil', async () => {
    server.use(http.get('/api/top', () => HttpResponse.json([])))
    renderWithProviders(<Home />)
    expect(await screen.findByRole('link', { name: /perfil/i })).toHaveAttribute('href', '/perfil')
  })

  it('muestra las postulaciones para dar seguimiento', async () => {
    const app = { ...application(1, 'aplicada'), seguimiento: true, dias_en_estado: 12 }
    server.use(http.get('/api/insights', () => HttpResponse.json(insights({ seguimiento: [app] }))))
    renderWithProviders(<Home />)
    expect(await screen.findByText(/hace 12 días/i)).toBeInTheDocument()
  })
})

// Un toque real: pointerdown y luego click en el mismo punto (Oferta 1 está en px 355, py 154).
function tap(canvas: HTMLElement, pointerType: 'touch' | 'mouse', button = 0) {
  fireEvent.pointerDown(canvas, { pointerType, button, clientX: 355, clientY: 154 })
  fireEvent.click(canvas, { button, clientX: 355, clientY: 154 })
}

describe('Mapa semántico', () => {
  const threePoints = () => server.use(http.get('/api/map', () =>
    HttpResponse.json({ total: 3, puntos: [mapPoint(1, 90, 0.2, -0.3), mapPoint(2, 70, -0.5, 0.4), mapPoint(3, null, 0.6, 0.6)] })))

  it('anuncia el resumen del mapa', async () => {
    threePoints()
    renderWithProviders(<Home />)
    expect(await screen.findByRole('img', { name: /3 ofertas; 2 con puntaje/ })).toBeInTheDocument()
  })

  it('sin ofertas en el mapa se ve el estado vacío', async () => {
    renderWithProviders(<Home />)
    expect(await screen.findByText(/el mapa se dibuja/i)).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /ofertas;/ })).toBeNull()
  })

  it('tocar dos veces abre el detalle', async () => {
    threePoints()
    server.use(http.get('/api/jobs/1', () => HttpResponse.json({
      job: job(1), descripcion_texto: 'Texto', match: null, etiqueta: null, postulacion: null,
    })))
    renderWithProviders(<Home />)
    const canvas = await screen.findByRole('img', { name: /3 ofertas/ })
    canvas.getBoundingClientRect = () => ({ left: 0, top: 0, width: 600, height: 420, right: 600, bottom: 420, x: 0, y: 0, toJSON() {} })
    // Oferta 1 está en (0.2, -0.3): px = 300 + 0.2·276 = 355.2, py = 210 − 0.3·186 = 154.2
    tap(canvas, 'touch')
    expect(await screen.findByRole('tooltip')).toHaveTextContent('Oferta 1')
    expect(screen.queryByRole('dialog')).toBeNull()
    tap(canvas, 'touch')
    expect(await screen.findByRole('dialog', { name: 'Detalle de la oferta' })).toBeInTheDocument()
  })

  it('deslizar sobre el mapa no muestra ni abre nada', async () => {
    threePoints()
    renderWithProviders(<Home />)
    const canvas = await screen.findByRole('img', { name: /3 ofertas/ })
    canvas.getBoundingClientRect = () => ({ left: 0, top: 0, width: 600, height: 420, right: 600, bottom: 420, x: 0, y: 0, toJSON() {} })
    // Un deslizamiento empieza con pointerdown pero el navegador no dispara click.
    fireEvent.pointerDown(canvas, { pointerType: 'touch', clientX: 355, clientY: 154 })
    fireEvent.pointerDown(canvas, { pointerType: 'touch', clientX: 355, clientY: 154 })
    expect(screen.queryByRole('tooltip')).toBeNull()
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('el clic derecho no abre el detalle', async () => {
    threePoints()
    renderWithProviders(<Home />)
    const canvas = await screen.findByRole('img', { name: /3 ofertas/ })
    canvas.getBoundingClientRect = () => ({ left: 0, top: 0, width: 600, height: 420, right: 600, bottom: 420, x: 0, y: 0, toJSON() {} })
    tap(canvas, 'mouse', 2)
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('con movimiento reducido el mapa no anima', async () => {
    media.reducedMotion = true
    threePoints()
    renderWithProviders(<Home />)
    expect(await screen.findByRole('img', { name: /3 ofertas/ })).toHaveAttribute('data-animating', 'false')
  })

  it('sin movimiento reducido el mapa anima', async () => {
    threePoints()
    renderWithProviders(<Home />)
    expect(await screen.findByRole('img', { name: /3 ofertas/ })).toHaveAttribute('data-animating', 'true')
  })

  it('si el mapa falla, se puede reintentar', async () => {
    let calls = 0
    server.use(http.get('/api/map', () => {
      calls += 1
      return calls === 1
        ? HttpResponse.json({ detail: 'Falló el mapa' }, { status: 500 })
        : HttpResponse.json({ total: 1, puntos: [mapPoint(1)] })
    }))
    renderWithProviders(<Home />)
    expect(await screen.findByText('Falló el mapa')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByRole('img', { name: /1 ofertas/ })).toBeInTheDocument()
  })
})
