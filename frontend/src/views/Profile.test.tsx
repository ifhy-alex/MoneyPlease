import { act, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { delay, http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import type { Perfil, ProfileVersion } from '../api/types'
import { job, server, skillsGraph } from '../test/handlers'
import { media, setMedia } from '../test/setup'
import { renderWithProviders } from '../test/render'
import Profile from './Profile'

const perfil: Perfil = {
  skills: [{ name: 'Java', level: 'intermedio' }],
  languages: [{ name: 'Inglés', level: 'B2' }],
  experience_months: 5,
  seniority_target: ['practica', 'junior'],
  roles_target: ['Backend Developer'],
  summary: 'Estudiante de Informática',
  preferences: {
    modalidad: ['presencial', 'hibrido', 'remoto'], ubicaciones: ['Cartago'], remoto_abierto: true,
    excluir_titulo: ['senior'], excluir_palabras: ['5+ years'],
  },
}
const areas = { backend: 2, frontend: 0, datos: 0, cloud: 0, testing: 0, idiomas: 0 }
const v = (version: number, p: Perfil = perfil): ProfileVersion => ({ version, creado_en: '2026-10-30T12:00:00Z', perfil: p, areas })

function withProfile() {
  const puts: Perfil[] = []
  server.use(
    http.get('/api/profile', () => HttpResponse.json(v(2))),
    http.get('/api/profile/versions', () => HttpResponse.json([v(2), v(1, { ...perfil, summary: 'Versión vieja' })])),
    http.put('/api/profile', async ({ request }) => {
      const body = (await request.json()) as Perfil
      puts.push(body)
      await delay(50)
      return HttpResponse.json(v(3, body), { status: 201 })
    }),
  )
  return puts
}

describe('Perfil', () => {
  it('editar el nivel de una skill y guardar envía el PUT', async () => {
    const puts = withProfile()
    renderWithProviders(<Profile />)
    // Con la suite completa en paralelo el formulario puede tardar más de 1 s en aparecer.
    await userEvent.selectOptions(await screen.findByLabelText(/nivel de java/i, {}, { timeout: 4000 }), 'avanzado')
    await userEvent.click(screen.getByRole('button', { name: /guardar versión/i }))
    await waitFor(() => expect(puts).toHaveLength(1))
    expect(puts[0].skills[0]).toMatchObject({ name: 'Java', level: 'avanzado' })
  })

  it('doble clic en guardar envía un solo PUT', async () => {
    const puts = withProfile()
    renderWithProviders(<Profile />)
    const button = await screen.findByRole('button', { name: /guardar versión/i })
    await userEvent.dblClick(button)
    await waitFor(() => expect(screen.getByRole('button', { name: /guardar versión/i })).toBeEnabled())
    expect(puts).toHaveLength(1)
  })

  it('un 422 muestra el error junto al campo', async () => {
    withProfile()
    server.use(http.put('/api/profile', () => HttpResponse.json(
      { detail: [{ loc: ['body', 'preferences', 'modalidad', 0], msg: 'Input should be presencial, hibrido or remoto' }] },
      { status: 422 })))
    renderWithProviders(<Profile />)
    await userEvent.click(await screen.findByRole('button', { name: /guardar versión/i }))
    const group = screen.getByRole('group', { name: /modalidad/i })
    expect(await within(group).findByText(/presencial, hibrido or remoto/)).toBeInTheDocument()
  })

  it('subir un CV llena el formulario sin guardar', async () => {
    const puts = withProfile()
    server.use(http.post('/api/profile/from-cv', () => HttpResponse.json({
      perfil: { ...perfil, summary: 'Borrador desde el CV' }, texto_enviado: 'PROFESSIONAL PROFILE ...',
    })))
    renderWithProviders(<Profile />)
    await screen.findByLabelText(/nivel de java/i)
    const file = new File(['%PDF-1.4'], 'cv.pdf', { type: 'application/pdf' })
    await userEvent.upload(screen.getByLabelText(/subir cv/i), file)
    expect(await screen.findByDisplayValue('Borrador desde el CV')).toBeInTheDocument()
    expect(screen.getByText(/texto enviado a gemini/i)).toBeInTheDocument()
    expect(puts).toHaveLength(0)
  })

  it('sin key muestra el mensaje del servidor', async () => {
    withProfile()
    server.use(http.post('/api/profile/from-cv', () => HttpResponse.json({ detail: 'Falta GEMINI_API_KEY en .env' }, { status: 503 })))
    renderWithProviders(<Profile />)
    await screen.findByLabelText(/nivel de java/i)
    await userEvent.upload(screen.getByLabelText(/subir cv/i), new File(['%PDF'], 'cv.pdf', { type: 'application/pdf' }))
    expect(await screen.findByText(/falta gemini_api_key/i)).toBeInTheDocument()
  })

  it('restaurar una versión hace PUT con ese perfil', async () => {
    const puts = withProfile()
    renderWithProviders(<Profile />)
    await userEvent.click(await screen.findByRole('button', { name: /restaurar versión 1/i }))
    await waitFor(() => expect(puts.at(-1)?.summary).toBe('Versión vieja'))
  })

  it('sin perfil invita a subir el CV', async () => {
    server.use(
      http.get('/api/profile', () => HttpResponse.json({ detail: 'no' }, { status: 404 })),
      http.get('/api/profile/versions', () => HttpResponse.json([])),
    )
    renderWithProviders(<Profile />)
    expect(await screen.findByText(/todavía no tienes perfil/i)).toBeInTheDocument()
  })
})

describe('Perfil: reintentar el mismo CV', () => {
  it('subir el mismo archivo dos veces envía dos peticiones', async () => {
    withProfile()
    let posts = 0
    server.use(http.post('/api/profile/from-cv', () => {
      posts += 1
      return HttpResponse.json({ detail: 'Gemini respondió que se agotó la cuota gratuita' }, { status: 429 })
    }))
    renderWithProviders(<Profile />)
    await screen.findByLabelText(/nivel de java/i)
    const file = new File(['%PDF-1.4'], 'cv.pdf', { type: 'application/pdf' })
    const input = screen.getByLabelText(/subir cv/i) as HTMLInputElement
    await userEvent.upload(input, file)
    await waitFor(() => expect(posts).toBe(1))
    expect(input.value).toBe('')
    await userEvent.upload(input, file)
    await waitFor(() => expect(posts).toBe(2))
  })
})

describe('Grafo de habilidades', () => {
  const withGraph = () => {
    withProfile()
    server.use(http.get('/api/skills-graph', () => HttpResponse.json(skillsGraph())))
  }

  it('muestra habilidades y marca las que faltan', async () => {
    withGraph()
    renderWithProviders(<Profile />)
    const graph = await screen.findByRole('group', { name: /grafo de habilidades/i })
    expect(within(graph).getByRole('button', { name: /java: 2 ofertas/i })).toHaveAttribute('data-tiene', 'true')
    expect(within(graph).getByRole('button', { name: /docker: 1 oferta/i })).toHaveAttribute('data-tiene', 'false')
    expect(await screen.findByText(/sin ofertas que las pidan/i)).toHaveTextContent('Python')
  })

  it('pasar sobre una habilidad atenúa lo que no está conectado', async () => {
    withGraph()
    renderWithProviders(<Profile />)
    const graph = await screen.findByRole('group', { name: /grafo de habilidades/i })
    await userEvent.hover(within(graph).getByRole('button', { name: /docker/i }))
    expect(within(graph).getByRole('button', { name: /abrir oferta 2/i })).toHaveAttribute('opacity', '0.2')
    expect(within(graph).getByRole('button', { name: /docker/i })).toHaveAttribute('opacity', '1')
  })

  it('con movimiento reducido el grafo no anima', async () => {
    media.reducedMotion = true
    withGraph()
    renderWithProviders(<Profile />)
    expect(await screen.findByRole('group', { name: /grafo de habilidades/i })).toHaveAttribute('data-animating', 'false')
  })

  it('la huella se dibuja con las versiones', async () => {
    withProfile()
    renderWithProviders(<Profile />)
    expect(await screen.findByRole('img', { name: /huella de 2 versiones/i })).toBeInTheDocument()
  })
})

describe('Detalle desde el grafo', () => {
  it('si marcar la oferta falla, avisa', async () => {
    withProfile()
    server.use(
      http.get('/api/skills-graph', () => HttpResponse.json(skillsGraph())),
      http.get('/api/jobs/1', () => HttpResponse.json({ job: job(1), descripcion_texto: 'x', match: null, etiqueta: null, postulacion: null })),
      http.post('/api/jobs/1/feedback', () => HttpResponse.json({ detail: 'No se pudo guardar la marca' }, { status: 500 })),
    )
    renderWithProviders(<Profile />)
    const graph = await screen.findByRole('group', { name: /grafo de habilidades/i })
    await userEvent.click(within(graph).getByRole('button', { name: /abrir oferta 1/i }))
    await userEvent.click(await screen.findByRole('button', { name: /^👍 me interesa/i }))
    expect(await screen.findByText('No se pudo guardar la marca')).toBeInTheDocument()
  })

  it('el grafo cambia de alto al girar el celular', async () => {
    withProfile()
    server.use(http.get('/api/skills-graph', () => HttpResponse.json(skillsGraph())))
    renderWithProviders(<Profile />)
    const graph = await screen.findByRole('group', { name: /grafo de habilidades/i })
    expect(graph).toHaveAttribute('height', '360')
    act(() => setMedia('narrow', true))
    await waitFor(() => expect(screen.getByRole('group', { name: /grafo de habilidades/i })).toHaveAttribute('height', '300'))
  })
})

describe('Enlace al grafo 3D', () => {
  it('el grafo ofrece verlo en 3D', async () => {
    withProfile()
    server.use(http.get('/api/skills-graph', () => HttpResponse.json(skillsGraph())))
    renderWithProviders(<Profile />)
    expect(await screen.findByRole('link', { name: /ver en 3d/i })).toHaveAttribute('href', '/universo?vista=habilidades')
  })
})
