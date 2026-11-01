import type { MapPoint } from '../api/types'

export type Tone = 'sin' | 'bajo' | 'alto'

export interface ScreenPoint extends MapPoint {
  px: number
  py: number
  r: number
  tone: Tone
}

/** Radio del punto: 1.5 px sin evaluar o con 0, hasta 3.5 px con 100. */
export function radiusFor(puntaje: number | null): number {
  return puntaje === null ? 1.5 : 1.5 + (Math.min(Math.max(puntaje, 0), 100) / 100) * 2
}

export function toneFor(puntaje: number | null): Tone {
  if (puntaje === null) return 'sin'
  return puntaje >= 60 ? 'alto' : 'bajo'
}

/** Coordenadas de la API (-1..1, el perfil en 0,0) a píxeles del lienzo, dejando un margen. */
export function layoutMap(points: MapPoint[], width: number, height: number, margin = 24): ScreenPoint[] {
  const sx = width / 2 - margin
  const sy = height / 2 - margin
  return points.map((p) => ({
    ...p, px: width / 2 + p.x * sx, py: height / 2 + p.y * sy, r: radiusFor(p.puntaje), tone: toneFor(p.puntaje),
  }))
}

export function nearestPoint(points: ScreenPoint[], x: number, y: number, maxDist = 14): ScreenPoint | null {
  let best: ScreenPoint | null = null
  let bestDist = maxDist
  for (const p of points) {
    const d = Math.hypot(p.px - x, p.py - y)
    if (d < bestDist) {
      best = p
      bestDist = d
    }
  }
  return best
}

/** Las mejores ofertas evaluadas: las que se unen con una línea al perfil. */
export function topLinks(points: ScreenPoint[], n = 6): ScreenPoint[] {
  return points.filter((p) => p.puntaje !== null).sort((a, b) => b.puntaje! - a.puntaje!).slice(0, n)
}
