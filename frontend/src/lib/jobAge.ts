import type { Job } from '../api/types'

/** A partir de esta edad la oferta se marca como antigua: probablemente ya no reciba postulaciones. */
export const OLD_DAYS = 30

const DAY = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Costa_Rica' })
export const LONG_DATE = new Intl.DateTimeFormat('es-CR', { timeZone: 'America/Costa_Rica', dateStyle: 'long' })

/** Días de calendario en Costa Rica entre dos instantes (ayer a las 23:30 ya es "ayer"). */
function calendarDays(from: Date, to: Date): number {
  const day = (d: Date) => Date.parse(DAY.format(d))
  return Math.max(0, Math.round((day(to) - day(from)) / 86_400_000))
}

function ago(days: number): string {
  if (days === 0) return 'hoy'
  if (days === 1) return 'ayer'
  if (days < OLD_DAYS) return `hace ${days} días`
  if (days >= 365) return 'hace más de un año'
  const months = Math.floor(days / 30)
  return `hace ${months} ${months === 1 ? 'mes' : 'meses'}`
}

/**
 * Qué tan vieja es la oferta, con el verbo que corresponde a lo que da cada fuente: Greenhouse solo da la última
 * actualización, las alertas de correo la llegada del correo, y JSearch nada (se usa la primera vez que la vio la app).
 */
export function jobAge(job: Job, now = new Date()): { text: string; iso: string; old: boolean } {
  const iso = job.publicado_en ?? job.primera_vez_visto
  const verb = !job.publicado_en ? 'Vista por primera vez'
    : job.fuente.startsWith('greenhouse:') ? 'Actualizada'
    : job.fuente === 'gmail' ? 'Recibida'
    : 'Publicada'
  const days = calendarDays(new Date(iso), now)
  return { text: `${verb} ${ago(days)}`, iso, old: days >= OLD_DAYS }
}
