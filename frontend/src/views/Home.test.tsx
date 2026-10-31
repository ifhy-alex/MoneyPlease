import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { application, insights, server } from '../test/handlers'
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
