import { describe, expect, it } from 'vitest'
import type { ApplicationItem, Estado } from '../api/types'
import { application } from '../test/handlers'
import { layoutPipeline } from './pipelineLayout'

const app = (id: number, estado: Estado, desde: string): ApplicationItem => ({ ...application(id, estado), estado_desde: desde })

describe('pipelineLayout', () => {
  it('cada etapa va en su columna, de izquierda a derecha', () => {
    const { nodes } = layoutPipeline([app(1, 'guardada', '2026-10-01'), app(2, 'aplicada', '2026-10-01'),
      app(3, 'entrevista', '2026-10-01'), app(4, 'oferta', '2026-10-01')], 1000, 300)
    const x = Object.fromEntries(nodes.map((n) => [n.estado, n.x]))
    expect(x.guardada).toBeLessThan(x.aplicada)
    expect(x.aplicada).toBeLessThan(x.entrevista)
    expect(x.entrevista).toBeLessThan(x.oferta)
    expect(x.oferta).toBeLessThan(820)
  })

  it('ordena por fecha dentro de la columna', () => {
    const { nodes } = layoutPipeline([app(1, 'aplicada', '2026-10-20'), app(2, 'aplicada', '2026-10-01')], 1000, 300)
    const y = Object.fromEntries(nodes.map((n) => [n.id, n.y]))
    expect(y[2]).toBeLessThan(y[1])
  })

  it('rechazada va a la columna lateral y no desplaza a las demás', () => {
    const base = [app(1, 'guardada', '2026-10-01'), app(2, 'aplicada', '2026-10-02')]
    const without = layoutPipeline(base, 1000, 300).nodes
    const withRejected = layoutPipeline([...base, app(3, 'rechazada', '2026-10-03')], 1000, 300).nodes
    expect(withRejected.find((n) => n.id === 3)!.x).toBeGreaterThan(820)
    for (const n of without) expect(withRejected.find((m) => m.id === n.id)!.y).toBe(n.y)
  })

  it('un camino por nodo, sin NaN', () => {
    const { nodes, paths } = layoutPipeline([app(1, 'oferta', '2026-10-01'), app(2, 'rechazada', '2026-10-01'),
      app(3, 'guardada', '2026-10-01')], 600, 240)
    expect(paths).toHaveLength(nodes.length)
    for (const p of paths) expect(p.d).not.toContain('NaN')
  })
})
