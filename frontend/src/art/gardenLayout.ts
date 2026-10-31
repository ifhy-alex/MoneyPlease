import { mulberry32 } from './random'

export type Stage = 0 | 1 | 2 | 3 | 'wilted'

export const STAGE: Record<string, Stage> = { guardada: 0, aplicada: 1, entrevista: 2, oferta: 3, rechazada: 'wilted' }

export interface Plant {
  id: number
  x: number
  y: number
  stage: Stage
}

/**
 * Una planta por postulación, en una grilla con un pequeño desplazamiento determinista por id:
 * las mismas postulaciones siempre quedan en el mismo lugar y nunca se pisan.
 */
export function plantLayout(apps: { id: number; estado: string }[], width: number, height: number): Plant[] {
  if (apps.length === 0) return []
  const sorted = [...apps].sort((a, b) => a.id - b.id)
  const cols = Math.max(1, Math.ceil(Math.sqrt((sorted.length * width) / height)))
  const rows = Math.ceil(sorted.length / cols)
  const cw = width / cols
  const ch = height / rows
  return sorted.map((app, i) => {
    const rnd = mulberry32(app.id)
    const col = i % cols
    const row = Math.floor(i / cols)
    return {
      id: app.id,
      x: cw * (col + 0.5) + (rnd() - 0.5) * cw * 0.4,
      y: ch * (row + 0.5) + (rnd() - 0.5) * ch * 0.3,
      stage: STAGE[app.estado] ?? 0,
    }
  })
}
