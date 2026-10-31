import type { SkillPoint } from '../api/types'
import { seeded } from './random'

const SECTORS = ['backend', 'frontend', 'datos', 'cloud', 'testing', 'idiomas', 'otros']

export interface Star {
  skill: string
  x: number
  y: number
  r: number
  opacity: number
  color: string
  area: string
}

/**
 * Una estrella por skill: el área define el sector angular, las más frecuentes quedan cerca del centro y son
 * más grandes. Brillo pleno si la tienes; coral si es una brecha que no tienes. Determinista por nombre.
 */
export function starLayout(skills: SkillPoint[], width: number, height: number): Star[] {
  if (skills.length === 0) return []
  const maxFreq = Math.max(...skills.map((s) => s.frecuencia), 1)
  const cx = width / 2
  const cy = height / 2
  const maxR = Math.min(width, height) / 2 - 12
  return skills.map((s) => {
    const rnd = seeded(s.skill)
    const sector = Math.max(0, SECTORS.indexOf(s.area))
    const span = (2 * Math.PI) / SECTORS.length
    const angle = sector * span + (0.15 + rnd() * 0.7) * span - Math.PI / 2
    const closeness = s.frecuencia / maxFreq
    const dist = maxR * (0.25 + 0.7 * (1 - closeness)) * (0.9 + rnd() * 0.1)
    return {
      skill: s.skill,
      area: s.area,
      x: Math.min(width, Math.max(0, cx + Math.cos(angle) * dist)),
      y: Math.min(height, Math.max(0, cy + Math.sin(angle) * dist)),
      r: 1.5 + 4.5 * Math.sqrt(closeness),
      opacity: s.tengo ? 1 : 0.35,
      color: s.brecha && !s.tengo ? 'var(--danger)' : 'var(--accent)',
    }
  })
}
