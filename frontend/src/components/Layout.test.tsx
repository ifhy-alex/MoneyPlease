import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { renderWithProviders } from '../test/render'
import { insights, server } from '../test/handlers'
import { Layout } from './Layout'

describe('Layout', () => {
  it('muestra las 4 secciones', () => {
    renderWithProviders(<Layout><p>contenido</p></Layout>)
    for (const name of ['Inicio', 'Explorar', 'Postulaciones', 'Perfil']) {
      expect(screen.getAllByRole('link', { name: new RegExp(name) }).length).toBeGreaterThan(0)
    }
    expect(screen.getByText('contenido')).toBeInTheDocument()
  })

  it('no hay selector de tema: la app es solo oscura', () => {
    renderWithProviders(<Layout><p /></Layout>)
    expect(screen.queryByRole('button', { name: /tema/i })).toBeNull()
  })

  it('muestra el banner de modo demo', async () => {
    server.use(http.get('/api/insights', () => HttpResponse.json(insights({ demo: true }))))
    renderWithProviders(<Layout><p /></Layout>)
    await waitFor(() => expect(screen.getByText(/modo demo/i)).toBeInTheDocument())
  })
})

// evita el aviso de import sin usar cuando se ejecuta solo este archivo
void render
