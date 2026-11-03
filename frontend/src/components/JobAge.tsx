import type { Job } from '../api/types'
import { jobAge, LONG_DATE, OLD_DAYS } from '../lib/jobAge'

/** "Publicada hace 3 días", con la fecha exacta al pasar el puntero; las de más de un mes se ven en rojo. */
export function JobAge({ job, className = '' }: { job: Job; className?: string }) {
  const { text, iso, old } = jobAge(job)
  const date = LONG_DATE.format(new Date(iso))
  return (
    <time dateTime={iso}
          title={old ? `${date} · Tiene más de ${OLD_DAYS} días: puede que ya esté cerrada` : date}
          className={`mono text-xs ${old ? 'text-danger' : 'text-muted'} ${className}`}>
      {text}
    </time>
  )
}
