import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { server } from '../test/handlers'
import { useFeedback, useMap, useSaveProfile, useSkillsGraph, useTop } from './hooks'
import type { Perfil } from './types'

function Probe() {
  useTop()
  useMap()
  const save = useSaveProfile()
  return <button type="button" onClick={() => save.mutate({} as Perfil)}>Guardar</button>
}

describe('hooks', () => {
  it('guardar el perfil vuelve a pedir el top y el mapa', async () => {
    const calls = { top: 0, map: 0 }
    server.use(
      http.get('/api/top', () => { calls.top += 1; return HttpResponse.json([]) }),
      http.get('/api/map', () => { calls.map += 1; return HttpResponse.json({ total: 0, puntos: [] }) }),
      http.put('/api/profile', () => HttpResponse.json({}, { status: 201 })),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={client}><Probe /></QueryClientProvider>)
    await waitFor(() => expect(calls).toEqual({ top: 1, map: 1 }))
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    await waitFor(() => expect(calls).toEqual({ top: 2, map: 2 }))
  })
})

describe('feedback', () => {
  it('marcar una oferta vuelve a pedir el grafo de habilidades', async () => {
    let graphCalls = 0
    server.use(
      http.get('/api/skills-graph', () => { graphCalls += 1; return HttpResponse.json({ habilidades: [], ofertas: [], aristas: [] }) }),
      http.post('/api/jobs/1/feedback', () => new HttpResponse(null, { status: 204 })),
    )
    function Probe2() {
      useSkillsGraph()
      const fb = useFeedback()
      return <button type="button" onClick={() => fb.mutate({ jobId: 1, valor: 'no_interesa' })}>Marcar</button>
    }
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={client}><Probe2 /></QueryClientProvider>)
    await waitFor(() => expect(graphCalls).toBe(1))
    await userEvent.click(screen.getByRole('button', { name: 'Marcar' }))
    await waitFor(() => expect(graphCalls).toBe(2))
  })
})
