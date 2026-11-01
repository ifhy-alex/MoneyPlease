import type { FlowPoint } from '../api/types'

export interface RiverSeries {
  semanas: string[]
  fuentes: string[]
  /** matrix[semana][fuente] = ofertas nuevas */
  matrix: number[][]
}

export function toSeries(flow: FlowPoint[]): RiverSeries {
  const semanas = [...new Set(flow.map((p) => p.semana))].sort()
  const fuentes = [...new Set(flow.map((p) => p.fuente))].sort()
  const index = new Map(flow.map((p) => [`${p.semana}|${p.fuente}`, p.nuevas]))
  const matrix = semanas.map((s) => fuentes.map((f) => index.get(`${s}|${f}`) ?? 0))
  // Las semanas vacías antes de la primera con datos deformarían el streamgraph: se recortan.
  const first = matrix.findIndex((row) => row.some((v) => v > 0))
  if (first < 0) return { semanas: [], fuentes: [], matrix: [] }
  return { semanas: semanas.slice(first), fuentes, matrix: matrix.slice(first) }
}

// Un color por tipo de fuente: plata, azul y grises azulados de la paleta medianoche y plata.
export const SOURCE_COLORS = ['var(--silver)', 'var(--glow)', '#8FA3D6', '#5E6E9C', '#B4BED4', '#3E4F86']
