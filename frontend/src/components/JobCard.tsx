import { motion } from 'framer-motion'
import type { DuplicateRef, MatchInfo, Job } from '../api/types'
import { usePrefersReducedMotion } from '../lib/motion'
import { CompanySeal } from './CompanySeal'
import { DuplicatesNote } from './DuplicatesNote'
import { JobAge } from './JobAge'
import { ScoreRing } from './ScoreRing'

const FIT_LABEL = { practica: 'Práctica', junior: 'Junior', no_aplica: 'No aplica' } as const

interface Props {
  job: Job
  match: MatchInfo | null
  saved?: boolean
  index?: number
  onInterest?: () => void
  onDismiss?: () => void
  onSave?: () => void
  onOpen?: () => void
  duplicados?: DuplicateRef[]
}

export function JobCard({ job, match, saved, index = 0, onInterest, onDismiss, onSave, onOpen, duplicados }: Props) {
  const reduced = usePrefersReducedMotion()
  return (
    <motion.article
      layout={!reduced}
      initial={reduced ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduced ? { opacity: 0, transition: { duration: 0 } } : { opacity: 0, x: -40, transition: { duration: 0.18 } }}
      transition={{ delay: reduced ? 0 : index * 0.04, duration: 0.2 }}
      className="glass glass-hover p-4"
    >
      <div className="flex items-start gap-3">
        <CompanySeal company={job.empresa} />
        <div className="min-w-0 flex-1">
          <h3 className="text-lg leading-snug">
            {onOpen ? (
              <button type="button" onClick={onOpen} className="text-left hover:text-accent">{job.titulo}</button>
            ) : job.titulo}
          </h3>
          <p className="text-sm text-muted">
            {job.empresa} · {job.ubicacion || 'Sin ubicación'} ({job.modalidad})
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <JobAge job={job} />
            {job.ambito === 'internacional' && (
              <span className="mono rounded-md border border-glow/60 px-1.5 text-[11px] text-silver">🌎 Internacional</span>
            )}
          </div>
        </div>
        {match && (
          <div className="flex flex-col items-center">
            <ScoreRing score={match.score} fit={match.fit} />
            <span className="mono text-[11px] uppercase tracking-wider text-muted">{FIT_LABEL[match.fit]}</span>
          </div>
        )}
      </div>
      {match && (
        <>
          <ul className="mt-3 flex flex-wrap gap-1.5 text-xs">
            {match.fortalezas.slice(0, 3).map((f) => (
              <li key={`f-${f}`} className="mono rounded-md border border-line px-2 py-0.5 text-silver">{f}</li>
            ))}
            {match.brechas.slice(0, 3).map((b) => (
              <li key={`b-${b}`} className="mono rounded-md border border-dashed border-danger/50 px-2 py-0.5 text-muted">{b}</li>
            ))}
          </ul>
          <p className="mt-2 text-sm text-muted">{match.resumen}</p>
        </>
      )}
      <div className="mt-2"><DuplicatesNote duplicados={duplicados} /></div>
      <div className="mt-3 flex flex-wrap gap-2 text-sm">
        {onInterest && <ActionButton label="Me interesa" icon="👍" onClick={onInterest} />}
        {onDismiss && <ActionButton label="No me interesa" icon="👎" onClick={onDismiss} />}
        {onSave && <ActionButton label={saved ? 'Guardada' : 'Guardar'} icon="🔖" onClick={onSave} disabled={saved} />}
        <a href={job.url} target="_blank" rel="noreferrer noopener"
           className="rounded-lg px-2 py-1 text-muted hover:bg-surface-strong hover:text-text">
          ↗ <span>Abrir oferta</span>
        </a>
      </div>
    </motion.article>
  )
}

function ActionButton({ label, icon, onClick, disabled }: { label: string; icon: string; onClick: () => void; disabled?: boolean }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-label={label}
            className="rounded-lg px-2 py-1 text-muted hover:bg-surface-strong hover:text-text disabled:opacity-60">
      <span aria-hidden="true">{icon}</span> <span className="hidden sm:inline">{label}</span>
    </button>
  )
}
