import { describe, expect, it } from 'vitest'
import { skillsGraph } from '../test/handlers'
import { layoutGraph } from './skillGraphLayout'

describe('skillGraphLayout', () => {
  it('misma semilla, mismas posiciones', () => {
    const a = layoutGraph(skillsGraph(), 600, 360, 3).nodes.map((n) => [n.id, n.x, n.y])
    const b = layoutGraph(skillsGraph(), 600, 360, 3).nodes.map((n) => [n.id, n.x, n.y])
    expect(a).toEqual(b)
  })

  it('todos los nodos quedan dentro del lienzo', () => {
    for (const n of layoutGraph(skillsGraph(), 320, 240).nodes) {
      expect(n.x).toBeGreaterThanOrEqual(n.r + 8)
      expect(n.x).toBeLessThanOrEqual(320 - n.r - 8)
      expect(n.y).toBeGreaterThanOrEqual(n.r + 8)
      expect(n.y).toBeLessThanOrEqual(240 - n.r - 8)
    }
  })

  it('un nodo por habilidad y por oferta, y una arista por relación', () => {
    const { nodes, links } = layoutGraph(skillsGraph(), 600, 360)
    expect(nodes.map((n) => n.id).sort()).toEqual(['o:1', 'o:2', 's:Docker', 's:Java', 's:Python'])
    expect(links.map((l) => `${l.source.id}-${l.target.id}`).sort()).toEqual(['s:Docker-o:1', 's:Java-o:1', 's:Java-o:2'])
  })

  it('el radio de una habilidad crece con su grado', () => {
    const byId = Object.fromEntries(layoutGraph(skillsGraph(), 600, 360).nodes.map((n) => [n.id, n]))
    expect(byId['s:Java'].r).toBe(10)
    expect(byId['s:Docker'].r).toBe(7.5)
    expect(byId['s:Python'].r).toBe(5)
    expect(byId['o:1'].r).toBe(3)
  })
})
