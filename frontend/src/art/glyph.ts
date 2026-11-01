import { seeded } from './random'
import type { Area } from '../api/types'

export const AREAS: Area[] = ['backend', 'frontend', 'datos', 'cloud', 'testing', 'idiomas']

/** Ejes de la huella (0..1) por versión; se normaliza contra el máximo de todas para poder compararlas. */
export function normalizeAreas(versions: { areas: Record<Area, number> }[]): number[][] {
  const raw = versions.map((v) => AREAS.map((a) => v.areas[a] ?? 0))
  const max = Math.max(0, ...raw.flat())
  return raw.map((axes) => axes.map((x) => (max > 0 ? x / max : 0)))
}

/** Puntos del polígono radial: un eje por área, empezando arriba. */
export function glyphPoints(axes: number[], radius: number): string {
  return axes
    .map((v, i) => {
      const a = -Math.PI / 2 + (i * 2 * Math.PI) / axes.length
      return `${(Math.cos(a) * v * radius).toFixed(2)},${(Math.sin(a) * v * radius).toFixed(2)}`
    })
    .join(' ')
}

/**
 * Huella generativa: 6 sectores (uno por área) con arcos concéntricos, como un código circular.
 * Más habilidad en un área = arcos más largos y más numerosos en su sector. Determinista por `seed`.
 */
export function fingerprintPaths(axes: number[], radius: number, seed: string): string[] {
  const rnd = seeded(seed)
  const sector = (2 * Math.PI) / axes.length
  const gap = sector * 0.12
  const arc = (r: number, a0: number, a1: number) => {
    const p = (a: number) => `${(Math.cos(a) * r).toFixed(2)} ${(Math.sin(a) * r).toFixed(2)}`
    return `M ${p(a0)} A ${r.toFixed(2)} ${r.toFixed(2)} 0 ${a1 - a0 > Math.PI ? 1 : 0} 1 ${p(a1)}`
  }
  return axes.flatMap((v, i) => {
    const start = -Math.PI / 2 + i * sector + gap / 2
    const span = sector - gap
    if (v <= 0) return [arc(radius * 0.35, start, start + span * 0.08)]
    const rings = 3 + Math.round(v * 4)
    return Array.from({ length: rings }, (_, j) => {
      const r = radius * (0.35 + (0.65 * (j + 1)) / rings)
      const length = span * (0.15 + 0.85 * v) * (0.6 + rnd() * 0.4)
      const offset = (span - length) * rnd()
      return arc(r, start + offset, start + offset + length)
    })
  })
}
