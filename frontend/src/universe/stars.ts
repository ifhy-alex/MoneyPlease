import type { UniversePoint } from '../api/types'
import type { Graph3dNode } from './graph3d'

export type Vec3 = [number, number, number]

export interface StarSpec {
  id: string
  pos: Vec3
  size: number
  color: string
  opacity: number
  ring: boolean
  kind: 'offer' | 'skill' | 'missing'
  label?: string
}

export interface Filters {
  minScore: number
  empresa: string | null
  fit: 'todas' | 'practica' | 'junior'
}

/** La API da coordenadas de −1 a 1; la escena las usa ×6 (un universo de ~12 unidades de diámetro). */
export const SCALE = 6
const DIM = 0.12

export const scaled = (p: { x: number; y: number; z: number }): Vec3 => [p.x * SCALE, p.y * SCALE, p.z * SCALE]

function passes(p: UniversePoint, f: Filters): boolean {
  if (f.minScore > 0 && (p.puntaje ?? -1) < f.minScore) return false
  if (f.empresa && p.empresa !== f.empresa) return false
  if (f.fit !== 'todas' && p.fit !== f.fit) return false
  return true
}

function look(puntaje: number | null): Pick<StarSpec, 'size' | 'color' | 'opacity'> {
  if (puntaje === null) return { size: 0.35, color: '#2547B8', opacity: 1 }
  if (puntaje >= 80) return { size: 1.1, color: '#FFFFFF', opacity: 1 }
  if (puntaje >= 60) return { size: 0.7, color: '#CBD5E1', opacity: 1 }
  return { size: 0.5, color: '#CBD5E1', opacity: 0.7 }
}

/** Una estrella por oferta; las que no pasan los filtros se apagan (no desaparecen). */
export function offerStars(puntos: UniversePoint[], f: Filters): StarSpec[] {
  return puntos.map((p) => {
    const base = look(p.puntaje)
    return {
      id: `o:${p.job_id}`, pos: scaled(p), ...base, opacity: passes(p, f) ? base.opacity : DIM,
      ring: p.duplicados.length > 0, kind: 'offer',
    }
  })
}

/** Posiciones de las mejores ofertas evaluadas: las que se unen al centro con una línea de luz. */
export function topLinks3d(puntos: UniversePoint[], n = 6): Vec3[] {
  return puntos.filter((p) => p.puntaje !== null).sort((a, b) => b.puntaje! - a.puntaje!).slice(0, n).map(scaled)
}

/** Estrellas del grafo 3D: tus habilidades en plata, las que faltan en rojo apagado, las ofertas pequeñas. */
export function skillStars(nodes: Graph3dNode[]): StarSpec[] {
  const maxDegree = Math.max(1, ...nodes.map((n) => n.grado ?? 0))
  return nodes.map((n) => {
    if (n.kind === 'offer') {
      const good = (n.puntaje ?? 0) >= 60
      return { id: n.id, pos: n.pos, size: 0.35, color: good ? '#FFFFFF' : '#2547B8', opacity: 1, ring: false, kind: 'offer' }
    }
    const size = 0.8 + (0.8 * (n.grado ?? 0)) / maxDegree
    return n.tiene
      ? { id: n.id, pos: n.pos, size, color: '#CBD5E1', opacity: 1, ring: false, kind: 'skill', label: n.label }
      : { id: n.id, pos: n.pos, size, color: '#E0626F', opacity: 0.8, ring: false, kind: 'missing', label: n.label }
  })
}
