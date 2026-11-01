import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, type Node3D } from 'd3-force-3d'
import type { SkillsGraph } from '../api/types'
import { mulberry32 } from '../art/random'
import type { Vec3 } from './stars'

export interface Graph3dNode {
  id: string
  kind: 'skill' | 'offer'
  label: string
  pos: Vec3
  tiene?: boolean
  puntaje?: number
  jobId?: number
  grado?: number
}

const TICKS = 300
const MEDIAN_RADIUS = 4.5
const MAX_RADIUS = 9

/** Grafo habilidades ↔ ofertas en 3D: simulación de fuerzas completa de una vez, con semilla fija. */
export function layoutGraph3d(g: SkillsGraph, seed = 1): { nodes: Graph3dNode[]; links: [string, string][]; isolated: string[] } {
  const rnd = mulberry32(seed)
  const spread = () => (rnd() - 0.5) * 20
  const sim: (Node3D & Omit<Graph3dNode, 'pos'>)[] = [
    ...g.habilidades.filter((s) => s.grado > 0).map((s) => ({
      id: `s:${s.nombre}`, kind: 'skill' as const, label: s.nombre, tiene: s.tiene, grado: s.grado,
      x: spread(), y: spread(), z: spread(),
    })),
    ...g.ofertas.map((o) => ({
      id: `o:${o.job_id}`, kind: 'offer' as const, label: o.titulo, puntaje: o.puntaje, jobId: o.job_id,
      x: spread(), y: spread(), z: spread(),
    })),
  ]
  const ids = new Set(sim.map((n) => n.id))
  const links: [string, string][] = g.aristas
    .map((e) => [`s:${e.habilidad}`, `o:${e.job_id}`] as [string, string])
    .filter(([a, b]) => ids.has(a) && ids.has(b))
  forceSimulation(sim, 3)
    .randomSource(rnd)
    .force('link', forceLink(links.map(([source, target]) => ({ source, target }))).id((n) => n.id as string).distance(4).strength(0.6))
    .force('charge', forceManyBody().strength(-60))
    .force('center', forceCenter(0, 0, 0))
    .force('collide', forceCollide((n: Node3D) => (n.kind === 'skill' ? 1.6 : 0.7)))
    .stop()
    .tick(TICKS)
  // La simulación no tiene tamaño fijo: se escala para que la distancia mediana al centro sea MEDIAN_RADIUS
  // (el grueso del grafo se reparte en la vista) y los nodos más lejanos se acercan hasta MAX_RADIUS.
  const dists = sim.map((n) => Math.hypot(n.x ?? 0, n.y ?? 0, n.z ?? 0)).sort((a, b) => a - b)
  const k = MEDIAN_RADIUS / Math.max(dists[Math.floor(dists.length / 2)] ?? 0, 1e-9)
  const nodes = sim.map(({ x, y, z, vx: _vx, vy: _vy, vz: _vz, index: _i, ...rest }) => {
    const p: Vec3 = [(x ?? 0) * k, (y ?? 0) * k, (z ?? 0) * k]
    const d = Math.hypot(...p)
    const pos = (d > MAX_RADIUS ? p.map((v) => (v * MAX_RADIUS) / d) : p) as Vec3
    return { ...(rest as Omit<Graph3dNode, 'pos'>), pos }
  })
  return { nodes, links, isolated: g.habilidades.filter((s) => s.grado === 0).map((s) => s.nombre) }
}
