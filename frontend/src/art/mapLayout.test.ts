import { describe, expect, it } from 'vitest'
import type { MapPoint } from '../api/types'
import { layoutMap, nearestPoint, radiusFor, toneFor, topLinks } from './mapLayout'

const pt = (job_id: number, x: number, y: number, puntaje: number | null = 70): MapPoint =>
  ({ job_id, titulo: `T${job_id}`, empresa: 'E', x, y, similitud: 0.5, puntaje, etiqueta: null })

describe('mapLayout', () => {
  it('escala (-1..1) a píxeles con margen', () => {
    const [c, corner] = layoutMap([pt(1, 0, 0), pt(2, 1, -1)], 600, 420)
    expect([c.px, c.py]).toEqual([300, 210])
    expect([corner.px, corner.py]).toEqual([576, 24])
  })

  it('radio y tono según el puntaje', () => {
    expect(radiusFor(null)).toBe(1.5)
    expect(radiusFor(0)).toBe(1.5)
    expect(radiusFor(100)).toBe(3.5)
    expect(toneFor(null)).toBe('sin')
    expect(toneFor(59)).toBe('bajo')
    expect(toneFor(60)).toBe('alto')
    expect(toneFor(100)).toBe('alto')
  })

  it('nearestPoint encuentra el punto dentro de 14 px', () => {
    const pts = layoutMap([pt(1, 0, 0)], 600, 420)
    expect(nearestPoint(pts, 310, 210)?.job_id).toBe(1)
    expect(nearestPoint(pts, 315, 210)).toBeNull()
  })

  it('topLinks: los mejores con puntaje, de mayor a menor', () => {
    const pts = layoutMap([pt(1, 0, 0, 50), pt(2, 0, 0, null), pt(3, 0, 0, 90), pt(4, 0, 0, 70)], 600, 420)
    expect(topLinks(pts, 2).map((p) => p.job_id)).toEqual([3, 4])
    expect(topLinks(pts).map((p) => p.job_id)).toEqual([3, 4, 1])
  })
})
