import { seeded } from './random'

const COLD = [0x1c, 0x2a, 0x5a]
const WARM = [0x5a, 0x2a, 0x3a]

const hex = (rgb: number[]) => `#${rgb.map((c) => Math.round(c).toString(16).padStart(2, '0')).join('')}`

export interface SkyParams {
  stars: { x: number; y: number; r: number; a: number }[]
  top: string
  bottom: string
}

/**
 * Cielo del día: la fecha es la semilla (cada día su cielo), la densidad sale de las ofertas nuevas
 * y el tono va de frío a cálido según el score promedio (40 → 90).
 */
export function skyParams(fecha: string, nuevas: number, scorePromedio: number | null): SkyParams {
  const rnd = seeded(fecha)
  const count = Math.min(300, 40 + 4 * Math.max(0, nuevas))
  const t = scorePromedio === null ? 0 : Math.min(1, Math.max(0, (scorePromedio - 40) / 50))
  const top = hex(COLD.map((c, i) => c + (WARM[i] - c) * t))
  const stars = Array.from({ length: count }, () => ({ x: rnd(), y: rnd(), r: 0.4 + rnd() * 1.4, a: 0.3 + rnd() * 0.7 }))
  return { stars, top, bottom: '#0b1020' }
}
