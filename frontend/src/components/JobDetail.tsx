import { useJob } from '../api/hooks'
import { CompanySeal } from './CompanySeal'
import { ScoreRing } from './ScoreRing'

interface Props {
  id: number
  onClose: () => void
  onInterest: () => void
  onDismiss: () => void
  onSave: () => void
}

/** Panel lateral con la descripción completa. El texto viene sin HTML y se muestra como texto plano. */
export function JobDetail({ id, onClose, onInterest, onDismiss, onSave }: Props) {
  const detail = useJob(id)
  const d = detail.data
  return (
    <aside role="dialog" aria-label="Detalle de la oferta"
           className="fixed inset-y-0 right-0 z-30 flex w-full max-w-xl flex-col gap-4 overflow-y-auto border-l border-line bg-bg/85 p-6 backdrop-blur-xl">
      <button type="button" onClick={onClose} className="self-end text-sm text-muted hover:text-text">Cerrar ✕</button>
      {detail.isLoading && <p className="text-muted">Cargando…</p>}
      {detail.isError && <p role="alert" className="text-danger">No se pudo cargar la oferta.</p>}
      {d && (
        <>
          <header className="flex items-start gap-3">
            <CompanySeal company={d.job.empresa} size={48} />
            <div className="flex-1">
              <h2 className="text-2xl leading-tight">{d.job.titulo}</h2>
              <p className="text-sm text-muted">{d.job.empresa} · {d.job.ubicacion} ({d.job.modalidad})</p>
            </div>
            {d.match && <ScoreRing score={d.match.score} fit={d.match.fit} size={56} />}
          </header>
          {d.match && (
            <section className="grid gap-3 text-sm sm:grid-cols-2">
              <div>
                <h3 className="text-base text-ok">Fortalezas</h3>
                <ul className="list-disc pl-5">{d.match.fortalezas.map((f) => <li key={f}>{f}</li>)}</ul>
              </div>
              <div>
                <h3 className="text-base text-danger">Brechas</h3>
                <ul className="list-disc pl-5">{d.match.brechas.map((b) => <li key={b}>{b}</li>)}</ul>
              </div>
              <p className="text-muted sm:col-span-2">{d.match.resumen}</p>
            </section>
          )}
          <div className="flex flex-wrap gap-2 text-sm">
            <button type="button" onClick={onInterest} className="rounded-lg border border-line px-3 py-1">👍 Me interesa</button>
            <button type="button" onClick={onDismiss} className="rounded-lg border border-line px-3 py-1">👎 No me interesa</button>
            <button type="button" onClick={onSave} disabled={d.postulacion !== null}
                    className="rounded-lg border border-line px-3 py-1 disabled:opacity-60">
              🔖 {d.postulacion ? `En postulaciones (${d.postulacion.estado})` : 'Guardar'}
            </button>
            <a href={d.job.url} target="_blank" rel="noreferrer noopener" className="rounded-lg border border-line px-3 py-1">↗ Abrir oferta</a>
          </div>
          <section className="flex flex-col gap-2 text-sm leading-relaxed">
            {d.descripcion_texto.split('\n').filter(Boolean).map((line, i) => <p key={i}>{line}</p>)}
          </section>
        </>
      )}
    </aside>
  )
}
