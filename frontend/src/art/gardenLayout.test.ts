import { describe, expect, it } from 'vitest'
import { plantLayout } from './gardenLayout'

describe('jardín de postulaciones', () => {
  const apps = [
    { id: 1, estado: 'guardada' }, { id: 2, estado: 'aplicada' }, { id: 3, estado: 'entrevista' },
    { id: 4, estado: 'oferta' }, { id: 5, estado: 'rechazada' },
  ]

  it('es determinista y asigna etapas', () => {
    const a = plantLayout(apps, 600, 200)
    expect(plantLayout(apps, 600, 200)).toEqual(a)
    expect(a.map((p) => p.stage)).toEqual([0, 1, 2, 3, 'wilted'])
  })

  it('las plantas quedan dentro del área y no se pisan', () => {
    const many = Array.from({ length: 30 }, (_, i) => ({ id: i + 1, estado: 'aplicada' }))
    const layout = plantLayout(many, 600, 200)
    for (const p of layout) {
      expect(p.x).toBeGreaterThanOrEqual(0)
      expect(p.x).toBeLessThanOrEqual(600)
      expect(p.y).toBeGreaterThanOrEqual(0)
      expect(p.y).toBeLessThanOrEqual(200)
    }
    const keys = new Set(layout.map((p) => `${Math.round(p.x)}|${Math.round(p.y)}`))
    expect(keys.size).toBe(30)
  })

  it('maneja 0 y 1 postulaciones', () => {
    expect(plantLayout([], 600, 200)).toEqual([])
    const [only] = plantLayout([{ id: 9, estado: 'oferta' }], 600, 200)
    expect(only.x).toBeGreaterThan(0)
    expect(only.x).toBeLessThan(600)
  })
})
