import { describe, expect, it } from 'vitest'
import type { SkillPoint } from '../api/types'
import { starLayout } from './constellationLayout'

const skill = (s: string, extra: Partial<SkillPoint> = {}): SkillPoint =>
  ({ skill: s, area: 'backend', frecuencia: 1, tengo: true, brecha: false, ...extra })

describe('constelación de habilidades', () => {
  it('es determinista y escala por frecuencia', () => {
    const skills = [skill('java', { frecuencia: 9 }), skill('docker', { area: 'cloud', frecuencia: 1 })]
    const a = starLayout(skills, 400, 300)
    expect(starLayout(skills, 400, 300)).toEqual(a)
    expect(a[0].r).toBeGreaterThan(a[1].r)
  })

  it('las brechas que no tienes van en color de alerta y tenues', () => {
    const [gap] = starLayout([skill('kubernetes', { tengo: false, brecha: true, area: 'cloud' })], 400, 300)
    expect(gap.color).toBe('var(--danger)')
    expect(gap.opacity).toBeLessThan(1)
  })

  it('las estrellas quedan dentro del lienzo', () => {
    const many = Array.from({ length: 40 }, (_, i) => skill(`s${i}`, { frecuencia: (i % 7) + 1, area: 'otros' }))
    for (const s of starLayout(many, 400, 300)) {
      expect(s.x).toBeGreaterThanOrEqual(0)
      expect(s.x).toBeLessThanOrEqual(400)
      expect(s.y).toBeGreaterThanOrEqual(0)
      expect(s.y).toBeLessThanOrEqual(300)
    }
  })

  it('sin skills devuelve vacío', () => {
    expect(starLayout([], 400, 300)).toEqual([])
  })
})
