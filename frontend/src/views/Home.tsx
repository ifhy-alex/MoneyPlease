import { AnimatePresence } from 'framer-motion'
import { lazy, Suspense, useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, errorMessage } from '../api/client'
import { useCreateApplication, useFeedback, useInsights, useTop, useUpdateApplication, type FeedbackValue } from '../api/hooks'
import { JobCard } from '../components/JobCard'
import { JobDetail } from '../components/JobDetail'
import { StatusStrip } from '../components/StatusStrip'
import { Toast, type ToastState } from '../components/Toast'
import { EmptyState } from '../decor/EmptyState'

const DAY = 24 * 3600 * 1000
const SemanticMap = lazy(() => import('../art/SemanticMap'))

export default function Home() {
  const top = useTop()
  const insights = useInsights()
  const feedback = useFeedback()
  const save = useCreateApplication()
  const update = useUpdateApplication()
  const [toast, setToast] = useState<ToastState | null>(null)
  const [open, setOpen] = useState<number | null>(null)
  const closeToast = useCallback(() => setToast(null), [])

  const sendFeedback = (jobId: number, valor: FeedbackValue, undoable = false) =>
    feedback.mutate({ jobId, valor }, {
      onSuccess: () => {
        if (undoable) {
          setToast({ message: 'Oferta ocultada', action: { label: 'Deshacer', onClick: () => sendFeedback(jobId, null) } })
        }
      },
      onError: (err) => setToast({ message: errorMessage(err), tone: 'error' }),
    })

  const saveJob = (jobId: number) =>
    save.mutate(jobId, {
      onSuccess: () => setToast({ message: 'Guardada en postulaciones' }),
      onError: (err) => {
        if (err instanceof ApiError && err.status === 409) return  // ya estaba guardada
        setToast({ message: errorMessage(err), tone: 'error' })
      },
    })

  const visible = (top.data ?? []).filter((i) => i.etiqueta !== 'mala')

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <h1>Ofertas de hoy</h1>
        {insights.data && <StatusStrip insights={insights.data} />}
      </header>

      <section aria-label="Mapa de ofertas">
        <Suspense fallback={null}><SemanticMap onOpen={setOpen} /></Suspense>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1fr_18rem]">
        <section aria-label="Top del día" className="flex flex-col gap-3">
          {top.isLoading && <p className="text-muted">Cargando ofertas…</p>}
          {top.isError && (
            <p role="alert" className="text-danger">
              No se pudo cargar el top. <button type="button" className="underline" onClick={() => top.refetch()}>Reintentar</button>
            </p>
          )}
          {top.data && visible.length === 0 && (
            <EmptyState kind="sin-ofertas" title="Todavía no hay ofertas evaluadas para mostrar."
                        text="Guarda tu perfil para que el matching empiece a puntuar ofertas.">
              <Link to="/perfil" className="text-accent underline">Ir a Perfil</Link>
            </EmptyState>
          )}
          <AnimatePresence initial={false}>
            {visible.map((item, i) => (
              <JobCard
                key={item.job.id}
                index={i}
                job={item.job}
                match={item.match}
                saved={item.postulacion_id !== null}
                onInterest={() => sendFeedback(item.job.id, 'interesa')}
                onDismiss={() => sendFeedback(item.job.id, 'no_interesa', true)}
                onSave={() => saveJob(item.job.id)}
              />
            ))}
          </AnimatePresence>
        </section>

        <aside className="flex flex-col gap-4">
          <section className="glass p-4">
            <h2 className="text-lg">Brechas de la semana</h2>
            {insights.data?.brechas_semana.length ? (
              <ol className="mt-2 flex flex-col gap-1 text-sm">
                {insights.data.brechas_semana.map((g) => (
                  <li key={g.skill} className="flex justify-between">
                    <span className="capitalize">{g.skill}</span>
                    <span className="text-muted">{g.n}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="mt-2 text-sm text-muted">Sin brechas registradas esta semana.</p>
            )}
          </section>

          {insights.data && insights.data.seguimiento.length > 0 && (
            <section className="glass p-4">
              <h2 className="text-lg">Para dar seguimiento</h2>
              <ul className="mt-2 flex flex-col gap-3 text-sm">
                {insights.data.seguimiento.map((a) => (
                  <li key={a.id}>
                    <p className="font-medium">{a.job.titulo} · {a.job.empresa}</p>
                    <p className="text-muted">Aplicaste hace {a.dias_en_estado} días</p>
                    <div className="mt-1 flex gap-3">
                      <button type="button" className="text-accent"
                              onClick={() => update.mutate({ id: a.id, changes: { recordatorio_hasta: new Date(Date.now() + 7 * DAY).toISOString() } })}>
                        Posponer 7 días
                      </button>
                      <button type="button" className="text-muted"
                              onClick={() => update.mutate({ id: a.id, changes: { recordatorio_hasta: new Date(Date.now() + 36500 * DAY).toISOString() } })}>
                        Hecho
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </aside>
      </div>
      {open !== null && (
        <JobDetail id={open} onClose={() => setOpen(null)} onInterest={() => sendFeedback(open, 'interesa')}
                   onDismiss={() => sendFeedback(open, 'no_interesa', true)} onSave={() => saveJob(open)} />
      )}
      <Toast toast={toast} onClose={closeToast} />
    </div>
  )
}
