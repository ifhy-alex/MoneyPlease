import { describe, expect, it } from 'vitest'
import { skillsGraph, universePoint } from '../test/handlers'
import { ease, flyTarget, isTap } from './camera'
import { layoutGraph3d } from './graph3d'
import { search } from './search'
import { offerStars, SCALE, topLinks3d, type Filters } from './stars'

const ALL: Filters = { minScore: 0, empresa: null, fit: 'todas' }

describe('estrellas', () => {
  it('tamaño y color según el puntaje', () => {
    const [hi, mid, lo, none] = offerStars([universePoint(1, 85), universePoint(2, 70), universePoint(3, 40), universePoint(4, null)], ALL)
    expect([hi.size, hi.color]).toEqual([1.1, '#FFFFFF'])
    expect([mid.size, mid.color]).toEqual([0.7, '#CBD5E1'])
    expect([lo.size, lo.color, lo.opacity]).toEqual([0.5, '#CBD5E1', 0.7])
    expect([none.size, none.color]).toEqual([0.35, '#2547B8'])
  })

  it('las filtradas quedan casi apagadas', () => {
    const pts = [universePoint(1, 90, 0, { empresa: 'HPE', fit: 'practica' }), universePoint(2, 50, 0, { empresa: 'ACME' })]
    expect(offerStars(pts, { ...ALL, minScore: 80 }).map((s) => s.opacity)).toEqual([1, 0.12])
    expect(offerStars(pts, { ...ALL, empresa: 'HPE' })[1].opacity).toBe(0.12)
    expect(offerStars(pts, { ...ALL, fit: 'practica' })[1].opacity).toBe(0.12)
  })

  it('escala la posición y marca el anillo de duplicados', () => {
    const [s] = offerStars([universePoint(1, 90, 0, { x: 0.5, y: -0.5, z: 0.1, duplicados: [9] })], ALL)
    expect(s.id).toBe('o:1')
    expect(s.pos).toEqual([0.5 * SCALE, -0.5 * SCALE, 0.1 * SCALE])
    expect(s.ring).toBe(true)
  })

  it('las líneas van a las mejores con puntaje', () => {
    const pts = [universePoint(1, 50), universePoint(2, null), universePoint(3, 95)]
    const round = (v: number[]) => v.map((x) => Math.round(x * 1e6) / 1e6)
    expect(topLinks3d(pts, 2).map(round)).toEqual([round([0.3 * SCALE, -0.3 * SCALE, 0.15 * SCALE]),
      round([0.1 * SCALE, -0.1 * SCALE, 0.05 * SCALE])])
  })
})

describe('búsqueda', () => {
  const items = [{ id: 'a', text: 'Intern - Bachelor’s Tech · HPE' }, { id: 'b', text: 'Ingeniería de Energía · ACME' },
    { id: 'c', text: 'HPE Support' }]

  it('ignora mayúsculas y acentos', () => {
    expect(search('hpe', items).map((r) => r.id)).toEqual(['c', 'a'])
    expect(search('energia', items).map((r) => r.id)).toEqual(['b'])
  })

  it('máximo 8 y vacío sin texto', () => {
    const many = Array.from({ length: 12 }, (_, i) => ({ id: `${i}`, text: `Data ${i}` }))
    expect(search('data', many)).toHaveLength(8)
    expect(search('  ', many)).toEqual([])
  })
})

describe('cámara', () => {
  it('se acerca al objetivo por la misma recta', () => {
    expect(flyTarget([0, 0, 0], [0, 0, 10])).toEqual([0, 0, 4])
  })

  it('suavizado en los extremos', () => {
    expect([ease(0), ease(0.5), ease(1), ease(2)]).toEqual([0, 0.5, 1, 1])
  })

  it('un toque es corto y sin desplazamiento', () => {
    expect(isTap(2, 3, 120)).toBe(true)
    expect(isTap(10, 0, 100)).toBe(false)
    expect(isTap(1, 1, 600)).toBe(false)
  })
})

describe('grafo 3D', () => {
  it('es determinista, queda cerca del origen y aparta las habilidades sin ofertas', () => {
    const a = layoutGraph3d(skillsGraph(), 3)
    const b = layoutGraph3d(skillsGraph(), 3)
    expect(a.nodes.map((n) => n.pos)).toEqual(b.nodes.map((n) => n.pos))
    // Escalado por la mediana (el grueso del grafo se reparte) y con tope para los nodos lejanos.
    const dists = a.nodes.map((n) => Math.hypot(...n.pos)).sort((x, y) => x - y)
    expect(dists[Math.floor(dists.length / 2)]).toBeCloseTo(4.5, 5)
    expect(dists.at(-1)!).toBeLessThanOrEqual(9 + 1e-9)
    expect(a.isolated).toEqual(['Python'])
    expect(a.links).toHaveLength(3)
  })
})

describe('estrellas de habilidades', () => {
  it('tuyas en plata, faltantes en rojo, ofertas pequeñas', async () => {
    const { skillStars } = await import('./stars')
    const byId = Object.fromEntries(skillStars(layoutGraph3d(skillsGraph()).nodes).map((s) => [s.id, s]))
    expect([byId['s:Java'].color, byId['s:Java'].size, byId['s:Java'].label]).toEqual(['#CBD5E1', 1.6, 'Java'])
    expect([byId['s:Docker'].color, byId['s:Docker'].kind, byId['s:Docker'].opacity]).toEqual(['#E0626F', 'missing', 0.8])
    expect([byId['o:1'].size, byId['o:1'].color, byId['o:2'].color]).toEqual([0.35, '#FFFFFF', '#2547B8'])
  })
})
