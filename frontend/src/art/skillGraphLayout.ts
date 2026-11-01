import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY, type SimulationNodeDatum } from 'd3-force'
import type { SkillsGraph } from '../api/types'
import { mulberry32 } from './random'

export interface GraphNode extends SimulationNodeDatum {
  id: string
  kind: 'skill' | 'offer'
  label: string
  x: number
  y: number
  r: number
  tiene?: boolean
  puntaje?: number
  jobId?: number
}

export interface GraphLink {
  source: GraphNode
  target: GraphNode
}

const TICKS = 300

/**
 * Posiciones del grafo habilidades ↔ ofertas. La simulación de d3-force se corre completa de una vez
 * con una semilla fija, así que el mismo grafo siempre queda igual (y se puede probar).
 */
export function layoutGraph(g: SkillsGraph, width: number, height: number, seed = 1): { nodes: GraphNode[]; links: GraphLink[]; isolated: string[] } {
  const rnd = mulberry32(seed)
  const maxDegree = Math.max(1, ...g.habilidades.map((s) => s.grado))
  const nodes: GraphNode[] = [
    // Las habilidades que ninguna oferta pide no tienen aristas: la repulsión las mandaría a las esquinas.
    ...g.habilidades.filter((s) => s.grado > 0).map((s) => ({
      id: `s:${s.nombre}`, kind: 'skill' as const, label: s.nombre, tiene: s.tiene,
      r: 5 + (5 * s.grado) / maxDegree, x: width * (0.2 + rnd() * 0.6), y: height * (0.2 + rnd() * 0.6),
    })),
    ...g.ofertas.map((o) => ({
      id: `o:${o.job_id}`, kind: 'offer' as const, label: o.titulo, puntaje: o.puntaje, jobId: o.job_id,
      r: 3, x: width * (0.1 + rnd() * 0.8), y: height * (0.1 + rnd() * 0.8),
    })),
  ]
  const byId = new Map(nodes.map((n) => [n.id, n]))
  const links: GraphLink[] = g.aristas
    .filter((e) => byId.has(`s:${e.habilidad}`) && byId.has(`o:${e.job_id}`))
    .map((e) => ({ source: byId.get(`s:${e.habilidad}`)!, target: byId.get(`o:${e.job_id}`)! }))

  const sim = forceSimulation(nodes)
    .randomSource(rnd)
    .force('link', forceLink<GraphNode, GraphLink>(links).distance(Math.min(width, height) / 5).strength(0.6))
    .force('charge', forceManyBody<GraphNode>().strength(-55))
    .force('center', forceCenter(width / 2, height / 2))
    .force('x', forceX<GraphNode>(width / 2).strength(0.08))
    .force('y', forceY<GraphNode>(height / 2).strength(0.12))
    .force('collide', forceCollide<GraphNode>((n) => n.r + 6))
    .stop()
  for (let i = 0; i < TICKS; i++) sim.tick()
  for (const n of nodes) {
    n.x = Math.min(Math.max(n.x, n.r + 8), width - n.r - 8)
    n.y = Math.min(Math.max(n.y, n.r + 8), height - n.r - 8)
  }
  return { nodes, links, isolated: g.habilidades.filter((s) => s.grado === 0).map((s) => s.nombre) }
}

/** Las etiquetas de los nodos de la mitad derecha se escriben hacia la izquierda, para que no se corten. */
export function labelSide(n: GraphNode, width: number): 'left' | 'right' {
  return n.x > width * 0.55 ? 'left' : 'right'
}
