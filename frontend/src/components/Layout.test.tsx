import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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

  it('el selector de tema cambia data-theme y lo recuerda', async () => {
    renderWithProviders(<Layout><p /></Layout>)
    expect(document.documentElement.dataset.theme).toBe('light')
    await userEvent.click(screen.getByRole('button', { name: /tema/i }))
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem('theme')).toBe('dark')
  })

  it('muestra el banner de modo demo', async () => {
    server.use(http.get('/api/insights', () => HttpResponse.json(insights({ demo: true }))))
    renderWithProviders(<Layout><p /></Layout>)
    await waitFor(() => expect(screen.getByText(/modo demo/i)).toBeInTheDocument())
  })
})

// evita el aviso de import sin usar cuando se ejecuta solo este archivo
void render
