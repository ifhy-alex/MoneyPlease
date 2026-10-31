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
