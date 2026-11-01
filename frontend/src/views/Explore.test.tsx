import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { delay, http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { job, server } from '../test/handlers'
import { renderWithProviders } from '../test/render'
import Explore from './Explore'

function trackJobs() {
  const requests: URLSearchParams[] = []
  server.use(
    http.get('/api/jobs', ({ request }) => {
      requests.push(new URL(request.url).searchParams)
      return HttpResponse.json({ items: [{ job: job(7, { titulo: 'Backend Intern' }), match: null, etiqueta: null }], total: 1, page: 1 })
    }),
    http.get('/api/jobs/7', () => HttpResponse.json({
      job: job(7, { titulo: 'Backend Intern' }), descripcion_texto: 'Hola\n<script>alert(1)</script>',
      match: null, etiqueta: null, postulacion: null,
    })),
  )
  return requests
}

describe('Explorar', () => {
  it('cambiar un filtro actualiza la petición', async () => {
    const requests = trackJobs()
    renderWithProviders(<Explore />)
    expect(await screen.findByText('Backend Intern')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText(/modalidad/i), 'remoto')
    await waitFor(() => expect(requests.at(-1)?.get('modalidad')).toBe('remoto'))
  })

  it('lee los filtros iniciales desde la URL', async () => {
    const requests = trackJobs()
    renderWithProviders(<Explore />, { route: '/explorar?modalidad=hibrido&page=2&solo_cr=1' })
    await waitFor(() => expect(requests.length).toBeGreaterThan(0))
    expect(requests[0].get('modalidad')).toBe('hibrido')
    expect(requests[0].get('page')).toBe('2')
    expect(requests[0].get('solo_cr')).toBe('true')
    expect(screen.getByLabelText(/modalidad/i)).toHaveValue('hibrido')
  })

  it('la búsqueda de texto espera a que termines de escribir', async () => {
    const requests = trackJobs()
    renderWithProviders(<Explore />)
    await screen.findByText('Backend Intern')
    await userEvent.type(screen.getByLabelText(/buscar/i), 'java')
    await waitFor(() => expect(requests.at(-1)?.get('q')).toBe('java'), { timeout: 2000 })
    expect(requests.filter((r) => r.get('q') === 'j').length).toBe(0)
  })

  it('el detalle muestra la descripción como texto, sin ejecutar HTML', async () => {
    trackJobs()
    renderWithProviders(<Explore />)
    await userEvent.click(await screen.findByRole('button', { name: 'Backend Intern' }))
    expect(await screen.findByText(/<script>alert\(1\)<\/script>/)).toBeInTheDocument()
    expect(document.querySelector('script')).toBeNull()
  })
})

describe('Feedback en Explorar', () => {
  it('el feedback del detalle es inmediato', async () => {
    trackJobs()
    server.use(http.post('/api/jobs/7/feedback', async () => { await delay('infinite'); return new HttpResponse(null, { status: 204 }) }))
    renderWithProviders(<Explore />)
    await userEvent.click(await screen.findByRole('button', { name: 'Backend Intern' }))
    const dismiss = await screen.findByRole('button', { name: /no me interesa/i })
    expect(dismiss).toHaveAttribute('aria-pressed', 'false')
    await userEvent.click(dismiss)
    await waitFor(() => expect(screen.getByRole('button', { name: /no me interesa/i })).toHaveAttribute('aria-pressed', 'true'))
  })
})

describe('Flujo de ingesta', () => {
  it('muestra el flujo de ofertas con tres semanas de datos', async () => {
    trackJobs()
    server.use(http.get('/api/insights/flow', () => HttpResponse.json([
      { semana: '2026-10-12', fuente: 'workday', nuevas: 4 },
      { semana: '2026-10-19', fuente: 'workday', nuevas: 6 },
      { semana: '2026-10-26', fuente: 'greenhouse', nuevas: 3 },
    ])))
    renderWithProviders(<Explore />)
    expect(await screen.findByRole('img', { name: /flujo de ofertas/i }, { timeout: 4000 })).toBeInTheDocument()
  })
})
