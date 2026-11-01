import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { application, server } from '../test/handlers'
import { media } from '../test/setup'
import { renderWithProviders } from '../test/render'
import Applications from './Applications'

function withApps(patchStatus = 200) {
  const patches: unknown[] = []
  // El mock guarda los cambios, como el servidor real: la lista se vuelve a pedir después de cada PATCH.
  const state = [application(1, 'guardada'), application(2, 'aplicada')]
  server.use(
    http.get('/api/applications', () => HttpResponse.json(state)),
    http.patch('/api/applications/:id', async ({ request, params }) => {
      const body = await request.json()
      patches.push({ id: Number(params.id), ...(body as object) })
      if (patchStatus !== 200) return HttpResponse.json({ detail: 'falló' }, { status: patchStatus })
      const i = state.findIndex((a) => a.id === Number(params.id))
      state[i] = { ...state[i], ...(body as object) }
      return HttpResponse.json(state[i])
    }),
  )
  return patches
}

async function openBoard() {
  renderWithProviders(<Applications />)
  await userEvent.click(await screen.findByRole('tab', { name: /tablero/i }))
}

describe('Postulaciones', () => {
  it('el pipeline es la vista por defecto y tiene un nodo por postulación', async () => {
    withApps()
    renderWithProviders(<Applications />)
    // El pipeline se carga con React.lazy: en una corrida completa puede tardar más de 1 s.
    expect(await screen.findAllByRole('button', { name: /editar oferta 10\d/i }, { timeout: 4000 })).toHaveLength(2)
  })

  it('una rechazada sigue siendo editable en el pipeline', async () => {
    server.use(http.get('/api/applications', () => HttpResponse.json([application(1), application(3, 'rechazada')])))
    renderWithProviders(<Applications />)
    await userEvent.click(await screen.findByRole('button', { name: /editar oferta 103/i }, { timeout: 4000 }))
    expect(screen.getByRole('dialog', { name: 'Oferta 103' })).toBeInTheDocument()
  })

  it('mover con el teclado cambia de columna y llama al PATCH', async () => {
    const patches = withApps()
    await openBoard()
    const column = screen.getByRole('region', { name: /guardada/i })
    await userEvent.selectOptions(within(column).getByLabelText(/mover oferta 101/i), 'aplicada')
    await waitFor(() => expect(patches).toEqual([{ id: 1, estado: 'aplicada' }]))
    expect(within(screen.getByRole('region', { name: /^aplicada/i })).getByText('Oferta 101')).toBeInTheDocument()
  })

  it('si el PATCH falla, la tarjeta vuelve', async () => {
    withApps(500)
    await openBoard()
    const column = screen.getByRole('region', { name: /guardada/i })
    await userEvent.selectOptions(within(column).getByLabelText(/mover oferta 101/i), 'aplicada')
    await waitFor(() =>
      expect(within(screen.getByRole('region', { name: /guardada/i })).getByText('Oferta 101')).toBeInTheDocument())
  })

  it('pasar a entrevista lanza el estallido de partículas', async () => {
    withApps()
    await openBoard()
    const column = screen.getByRole('region', { name: /^aplicada/i })
    await userEvent.selectOptions(within(column).getByLabelText(/mover oferta 102/i), 'entrevista')
    expect(await screen.findByTestId('burst')).toBeInTheDocument()
  })

  it('con movimiento reducido no hay estallido', async () => {
    media.reducedMotion = true
    withApps()
    await openBoard()
    const column = screen.getByRole('region', { name: /^aplicada/i })
    await userEvent.selectOptions(within(column).getByLabelText(/mover oferta 102/i), 'entrevista')
    await waitFor(() => expect(screen.queryByTestId('burst')).not.toBeInTheDocument())
  })

  it('el editor guarda las notas', async () => {
    const patches = withApps()
    await openBoard()
    await userEvent.click(screen.getByRole('button', { name: /editar oferta 101/i }))
    const dialog = screen.getByRole('dialog')
    await userEvent.type(within(dialog).getByLabelText(/notas/i), 'Llamar el lunes')
    await userEvent.click(within(dialog).getByRole('button', { name: /guardar/i }))
    await waitFor(() => expect(patches.at(-1)).toMatchObject({ id: 1, notas: 'Llamar el lunes' }))
  })

  it('sin postulaciones muestra el estado vacío', async () => {
    renderWithProviders(<Applications />)
    expect(await screen.findByText(/todavía no guardaste/i)).toBeInTheDocument()
  })
})

describe('Borrar una postulación', () => {
  function trackDeletes() {
    const deletes: number[] = []
    server.use(http.delete('/api/applications/:id', ({ params }) => {
      deletes.push(Number(params.id))
      return new HttpResponse(null, { status: 204 })
    }))
    return deletes
  }

  it('pide confirmación y cancelar no borra', async () => {
    withApps()
    const deletes = trackDeletes()
    await openBoard()
    await userEvent.click(screen.getByRole('button', { name: /editar oferta 101/i }))
    await userEvent.click(screen.getByRole('button', { name: 'Eliminar' }))
    const confirm = screen.getByRole('dialog', { name: /¿borrar esta postulación\?/i })
    await userEvent.click(within(confirm).getByRole('button', { name: 'Cancelar' }))
    expect(screen.queryByRole('dialog', { name: /¿borrar/i })).not.toBeInTheDocument()
    expect(deletes).toEqual([])
  })

  it('confirmar borra', async () => {
    withApps()
    const deletes = trackDeletes()
    await openBoard()
    await userEvent.click(screen.getByRole('button', { name: /editar oferta 101/i }))
    await userEvent.click(screen.getByRole('button', { name: 'Eliminar' }))
    const confirm = screen.getByRole('dialog', { name: /¿borrar esta postulación\?/i })
    await userEvent.click(within(confirm).getByRole('button', { name: 'Eliminar' }))
    await waitFor(() => expect(deletes).toEqual([1]))
  })
})

describe('Confirmación de borrado', () => {
  it('la confirmación cubre toda la pantalla y su fondo solo la cierra a ella', async () => {
    withApps()
    await openBoard()
    await userEvent.click(screen.getByRole('button', { name: /editar oferta 101/i }))
    const editor = screen.getByRole('dialog', { name: 'Oferta 101' })
    await userEvent.click(screen.getByRole('button', { name: 'Eliminar' }))
    const confirm = screen.getByRole('dialog', { name: /¿borrar esta postulación\?/i })
    expect(editor.contains(confirm)).toBe(false)
    fireEvent.mouseDown(confirm.parentElement!)
    expect(screen.queryByRole('dialog', { name: /¿borrar/i })).not.toBeInTheDocument()
    expect(screen.getByRole('dialog', { name: 'Oferta 101' })).toBeInTheDocument()
  })

  it('el estallido sale de la tarjeta que se movió', async () => {
    const { burstOrigin } = await import('../art/ParticleBurst')
    document.body.innerHTML = '<div data-app-id="5"></div>'
    const el = document.querySelector<HTMLElement>('[data-app-id="5"]')!
    el.getBoundingClientRect = () => ({ left: 100, top: 40, width: 200, height: 60 } as DOMRect)
    expect(burstOrigin(5)).toEqual({ x: 200, y: 70 })
    expect(burstOrigin(99)).toBeNull()
  })
})
