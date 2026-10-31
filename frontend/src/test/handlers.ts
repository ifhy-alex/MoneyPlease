import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import type { ApplicationItem, Insights, TopItem } from '../api/types'

export const job = (id: number, extra: Partial<TopItem['job']> = {}): TopItem['job'] => ({
  id, titulo: `Oferta ${id}`, empresa: 'ACME', ubicacion: 'Heredia, Costa Rica', modalidad: 'hibrido', pais: 'CR',
  url: `https://x/${id}`, fuente: 'greenhouse:x', publicado_en: null, primera_vez_visto: '2026-10-30T12:00:00Z',
  ...extra,
})

export const topItem = (id: number, score = 80): TopItem => ({
  job: job(id),
  match: { score, fit: 'junior', fortalezas: ['Java'], brechas: ['Docker'], resumen: 'Buen encaje' },
  etiqueta: null,
  postulacion_id: null,
})

export const insights = (extra: Partial<Insights> = {}): Insights => ({
  demo: false,
  brechas_semana: [{ skill: 'kubernetes', n: 3 }],
  estado: { ultima_ingesta: '2026-10-30T12:00:00Z', fuentes_con_error: [], matching: null, pendientes: 0 },
  punto_control: { relevantes: 2, etiquetadas: 3 },
  seguimiento: [],
  ...extra,
})

export const application = (id: number, estado: ApplicationItem['estado'] = 'guardada'): ApplicationItem => ({
  id, estado, notas: '', fecha_aplicacion: null, siguiente_paso: '', estado_desde: '2026-10-30T12:00:00Z',
  recordatorio_hasta: null, seguimiento: false, dias_en_estado: 0, job: job(100 + id), match: null,
})

export const handlers = [
  http.get('/api/insights', () => HttpResponse.json(insights())),
  http.get('/api/top', () => HttpResponse.json([topItem(1, 90), topItem(2, 70)])),
  http.get('/api/insights/skills', () => HttpResponse.json([])),
  http.get('/api/insights/daily', () => HttpResponse.json([])),
  http.get('/api/insights/flow', () => HttpResponse.json([])),
  http.get('/api/applications', () => HttpResponse.json([])),
]

export const server = setupServer(...handlers)
