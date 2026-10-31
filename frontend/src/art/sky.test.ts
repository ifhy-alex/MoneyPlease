import { describe, expect, it } from 'vitest'
import { skyParams } from './sky'

describe('cielo del día', () => {
  it('es determinista por fecha', () => {
    expect(skyParams('2026-10-30', 10, 80)).toEqual(skyParams('2026-10-30', 10, 80))
    expect(skyParams('2026-10-30', 10, 80).stars).not.toEqual(skyParams('2026-10-31', 10, 80).stars)
  })

  it('la cantidad de estrellas crece con las ofertas nuevas y tiene tope', () => {
    expect(skyParams('2026-10-30', 0, null).stars).toHaveLength(40)
    expect(skyParams('2026-10-30', 10, null).stars).toHaveLength(80)
    expect(skyParams('2026-10-30', 1000, null).stars).toHaveLength(300)
  })

  it('el tono va de frío (score bajo o nulo) a cálido (score alto)', () => {
    expect(skyParams('2026-10-30', 5, null).top).toBe('#1c2a5a')
    expect(skyParams('2026-10-30', 5, 40).top).toBe('#1c2a5a')
    expect(skyParams('2026-10-30', 5, 90).top).toBe('#5a2a3a')
    const mid = skyParams('2026-10-30', 5, 65).top
    expect(mid).not.toBe('#1c2a5a')
    expect(mid).not.toBe('#5a2a3a')
  })

  it('las estrellas quedan en el rango 0..1', () => {
    for (const s of skyParams('2026-01-01', 50, 70).stars) {
      expect(s.x).toBeGreaterThanOrEqual(0)
      expect(s.x).toBeLessThanOrEqual(1)
      expect(s.y).toBeGreaterThanOrEqual(0)
      expect(s.y).toBeLessThanOrEqual(1)
    }
  })
})
