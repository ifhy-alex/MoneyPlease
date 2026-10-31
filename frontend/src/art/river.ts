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
  return { semanas, fuentes, matrix }
}

// Un color por tipo de fuente, derivado de los acentos del tema.
export const SOURCE_COLORS = ['var(--accent)', 'var(--ok)', 'var(--danger)', '#8b9cf7', '#c58cf2', '#5fc9d9']
