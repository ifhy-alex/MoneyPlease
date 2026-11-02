import type { Vec3 } from './stars'

/** Punto a `distance` del objetivo sobre la recta cámara→objetivo: se llega mirando en la misma dirección. */
export function flyTarget(target: Vec3, camera: Vec3, distance = 4): Vec3 {
  const d: Vec3 = [camera[0] - target[0], camera[1] - target[1], camera[2] - target[2]]
  const len = Math.hypot(...d) || 1
  return [target[0] + (d[0] / len) * distance, target[1] + (d[1] / len) * distance, target[2] + (d[2] / len) * distance]
}

/** easeInOutCubic, limitado a [0, 1]. */
export function ease(t: number): number {
  const x = Math.min(Math.max(t, 0), 1)
  return x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2
}

/** Un toque de verdad: corto y casi sin moverse (arrastrar para rotar no cuenta). */
export function isTap(dx: number, dy: number, ms: number): boolean {
  return Math.hypot(dx, dy) < 6 && ms < 400
}

/**
 * La estrella que se elige con el puntero: la más cercana al rayo entre las visibles. Las apagadas por un filtro
 * o por un resaltado (opacidad < minAlpha) no se pueden tocar.
 */
export function pickVisible(hits: { index?: number; distanceToRay?: number }[], alphas: ArrayLike<number>,
                            minAlpha = 0.3): number | null {
  let best: number | null = null
  let bestDist = Infinity
  for (const h of hits) {
    if (h.index === undefined || (alphas[h.index] ?? 0) < minAlpha) continue
    const d = h.distanceToRay ?? 0
    if (d < bestDist) {
      best = h.index
      bestDist = d
    }
  }
  return best
}
