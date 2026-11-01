import type { ApplicationItem, Estado } from '../api/types'

export const STAGES = ['guardada', 'aplicada', 'entrevista', 'oferta'] as const
const MAIN = 0.82  // el 82 % izquierdo para las 4 etapas; el resto, para las rechazadas

export interface PipeNode {
  id: number
  estado: Estado
  x: number
  y: number
  seguimiento: boolean
  titulo: string
}

export const columnX = (stage: number, width: number) => (width * MAIN * (stage + 0.5)) / STAGES.length
export const sideX = (width: number) => width * MAIN + (width * (1 - MAIN)) / 2

/**
 * Nodos del pipeline: una columna por etapa (más una lateral para rechazadas), ordenados por fecha dentro de
 * cada columna. Cada nodo trae un camino que sale del centro de la primera columna y pasa por las etapas previas.
 */
export function layoutPipeline(apps: ApplicationItem[], width: number, height: number): { nodes: PipeNode[]; paths: { id: number; d: string }[] } {
  const groups = new Map<string, ApplicationItem[]>()
  for (const a of apps) groups.set(a.estado, [...(groups.get(a.estado) ?? []), a])
  const nodes: PipeNode[] = []
  for (const [estado, list] of groups) {
    const sorted = [...list].sort((a, b) => a.estado_desde.localeCompare(b.estado_desde) || a.id - b.id)
    const stage = STAGES.indexOf(estado as (typeof STAGES)[number])
    const x = stage >= 0 ? columnX(stage, width) : sideX(width)
    sorted.forEach((a, k) => nodes.push({
      id: a.id, estado: a.estado, x, y: (height * (k + 1)) / (sorted.length + 1), seguimiento: a.seguimiento, titulo: a.job.titulo,
    }))
  }
  const paths = nodes.map((n) => ({ id: n.id, d: pathFor(n, width, height) }))
  return { nodes, paths }
}

function pathFor(n: PipeNode, width: number, height: number): string {
  const stage = STAGES.indexOf(n.estado as (typeof STAGES)[number])
  // Etapas por las que pasó: las anteriores a la suya; una rechazada pasó por guardada y aplicada.
  const stops = stage >= 0 ? STAGES.slice(0, stage + 1).map((_, i) => columnX(i, width))
    : [columnX(0, width), columnX(1, width), sideX(width)]
  const x0 = stops[0]
  if (stops.length === 1) return `M ${(x0 - 14).toFixed(1)} ${n.y.toFixed(1)} L ${x0.toFixed(1)} ${n.y.toFixed(1)}`
  const mid = height / 2
  const x1 = stops[1]
  const cx = (x0 + x1) / 2
  let d = `M ${x0.toFixed(1)} ${mid.toFixed(1)} C ${cx.toFixed(1)} ${mid.toFixed(1)}, ${cx.toFixed(1)} ${n.y.toFixed(1)}, ${x1.toFixed(1)} ${n.y.toFixed(1)}`
  for (const x of stops.slice(2)) d += ` L ${x.toFixed(1)} ${n.y.toFixed(1)}`
  return d
}
