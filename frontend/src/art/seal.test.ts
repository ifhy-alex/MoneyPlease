import { describe, expect, it } from 'vitest'
import { fnv1a, sealParams } from './seal'

describe('sello de empresa', () => {
  it('es determinista', () => {
    expect(sealParams('Konrad Group')).toEqual(sealParams('Konrad Group'))
    expect(sealParams('KONRAD group ')).toEqual(sealParams('konrad group'))
  })

  it('cambia entre empresas', () => {
    const names = Array.from({ length: 20 }, (_, i) => `Empresa ${i}`)
    const distinct = new Set(names.map((n) => JSON.stringify(sealParams(n))))
    expect(distinct.size).toBeGreaterThan(15)
  })

  it('mantiene los rangos y acepta nombre vacío', () => {
    for (const n of ['', 'a', 'Pura Vida Tech']) {
      const p = sealParams(n)
      expect(p.sides).toBeGreaterThanOrEqual(3)
      expect(p.sides).toBeLessThanOrEqual(8)
      expect(p.rings).toBeGreaterThanOrEqual(1)
      expect(p.rings).toBeLessThanOrEqual(3)
      expect(p.hue).toBeGreaterThanOrEqual(0)
      expect(p.hue).toBeLessThan(360)
    }
    expect(fnv1a('')).toBe(fnv1a(''))
  })
})
