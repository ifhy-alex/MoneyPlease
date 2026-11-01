import { lazy, Suspense, useCallback, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ApiError, errorMessage } from '../api/client'
import { useCreateApplication, useFeedback, useJobs, type FeedbackValue } from '../api/hooks'
import { Filters, filtersFromParams } from '../components/Filters'
import { JobCard } from '../components/JobCard'
import { JobDetail } from '../components/JobDetail'
import { Toast, type ToastState } from '../components/Toast'
import { EmptyState } from '../decor/EmptyState'

const SignalFlow = lazy(() => import('../art/SignalFlow'))
const PAGE = 25

export default function Explore() {
  const [params, setParams] = useSearchParams()
  const filters = filtersFromParams(params)
  const jobs = useJobs(filters)
  const feedback = useFeedback()
  const save = useCreateApplication()
  const [open, setOpen] = useState<number | null>(null)
  const [toast, setToast] = useState<ToastState | null>(null)
  const closeToast = useCallback(() => setToast(null), [])
  const page = filters.page ?? 1
  const pages = Math.max(1, Math.ceil((jobs.data?.total ?? 0) / PAGE))

  const goTo = (p: number) => setParams((prev) => {
    const next = new URLSearchParams(prev)
    if (p > 1) next.set('page', String(p))
    else next.delete('page')
    return next
  })
  const sendFeedback = (jobId: number, valor: FeedbackValue) =>
    feedback.mutate({ jobId, valor }, {
      onSuccess: () => setToast({ message: valor === null ? 'Marca quitada' : valor === 'interesa' ? 'Marcada como interesante' : 'Marcada como no interesante' }),
      onError: (err) => setToast({ message: errorMessage(err), tone: 'error' }),
    })
  const saveJob = (jobId: number) => save.mutate(jobId, {
    onSuccess: () => setToast({ message: 'Guardada en postulaciones' }),
    onError: (err) => !(err instanceof ApiError && err.status === 409) && setToast({ message: errorMessage(err), tone: 'error' }),
  })

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-3">
        <h1>Explorar ofertas</h1>
        <Suspense fallback={null}><SignalFlow /></Suspense>
        <Filters />
      </header>
      <p className="text-sm text-muted" aria-live="polite">
        {jobs.data ? `${jobs.data.total} ofertas` : jobs.isLoading ? 'Cargando…' : ''}
      </p>
      {jobs.isError && <p role="alert" className="text-danger">No se pudieron cargar las ofertas.</p>}
      {jobs.data && jobs.data.total === 0 && (
        <EmptyState kind="sin-ofertas" title="Ninguna oferta coincide con estos filtros." text="Prueba quitando alguno." />
      )}
      <div className="grid gap-3 xl:grid-cols-2">
        {jobs.data?.items.map((item) => (
          <JobCard key={item.job.id} job={item.job} match={item.match} onOpen={() => setOpen(item.job.id)}
                   onSave={() => saveJob(item.job.id)} />
        ))}
      </div>
      {pages > 1 && (
        <nav aria-label="Paginación" className="flex items-center justify-center gap-4 text-sm">
          <button type="button" disabled={page <= 1} onClick={() => goTo(page - 1)} className="disabled:opacity-40">← Anterior</button>
          <span>Página {page} de {pages}</span>
          <button type="button" disabled={page >= pages} onClick={() => goTo(page + 1)} className="disabled:opacity-40">Siguiente →</button>
        </nav>
      )}
      {open !== null && (
        <JobDetail id={open} onClose={() => setOpen(null)} onFeedback={(valor) => sendFeedback(open, valor)}
                   onSave={() => saveJob(open)} />
      )}
      <Toast toast={toast} onClose={closeToast} />
    </div>
  )
}
