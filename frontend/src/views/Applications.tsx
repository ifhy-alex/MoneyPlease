import { lazy, Suspense, useCallback, useState } from 'react'
import { errorMessage } from '../api/client'
import { useApplications, useDeleteApplication, useUpdateApplication, type ApplicationChanges } from '../api/hooks'
import type { ApplicationItem, Estado } from '../api/types'
import { ApplicationEditor } from '../components/ApplicationEditor'
import { Kanban } from '../components/Kanban'
import { Toast, type ToastState } from '../components/Toast'
import { usePrefersReducedMotion } from '../lib/motion'

const Garden = lazy(() => import('../art/Garden'))
const Starfall = lazy(() => import('../art/Starfall'))
const CELEBRATE: Estado[] = ['entrevista', 'oferta']

export default function Applications() {
  const apps = useApplications()
  const update = useUpdateApplication()
  const remove = useDeleteApplication()
  const reduced = usePrefersReducedMotion()
  const [view, setView] = useState<'jardin' | 'tablero'>('jardin')
  const [editing, setEditing] = useState<ApplicationItem | null>(null)
  const [stars, setStars] = useState(0)
  const [toast, setToast] = useState<ToastState | null>(null)
  const closeToast = useCallback(() => setToast(null), [])
  const endStars = useCallback(() => setStars(0), [])

  const change = (id: number, changes: ApplicationChanges) =>
    update.mutate({ id, changes }, {
      onSuccess: () => {
        if (changes.estado && CELEBRATE.includes(changes.estado) && !reduced) setStars(Date.now())
      },
      onError: (err) => setToast({ message: errorMessage(err), tone: 'error' }),
    })

  const list = apps.data ?? []
  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-3xl">Postulaciones</h1>
        <div role="tablist" aria-label="Vista" className="flex gap-1 rounded-xl border border-line p-1 text-sm">
          {(['jardin', 'tablero'] as const).map((v) => (
            <button key={v} type="button" role="tab" aria-selected={view === v} onClick={() => setView(v)}
                    className={`rounded-lg px-3 py-1 ${view === v ? 'bg-surface text-accent' : 'text-muted'}`}>
              {v === 'jardin' ? 'Jardín' : 'Tablero'}
            </button>
          ))}
        </div>
      </header>
      {apps.isLoading && <p className="text-muted">Cargando…</p>}
      {apps.data && list.length === 0 && (
        <div className="rounded-[var(--radius-card)] border border-line bg-surface p-6 text-center">
          <p className="font-display text-lg">Todavía no guardaste ninguna oferta.</p>
          <p className="mt-1 text-sm text-muted">Usa 🔖 Guardar en Inicio o Explorar para plantar la primera.</p>
        </div>
      )}
      {list.length > 0 && (view === 'jardin' ? (
        <Suspense fallback={null}><Garden apps={list} onSelect={setEditing} /></Suspense>
      ) : (
        <Kanban apps={list} onMove={(id, estado) => change(id, { estado })} onEdit={setEditing} />
      ))}
      {editing && (
        <ApplicationEditor
          app={editing}
          onClose={() => setEditing(null)}
          onSave={(changes) => { change(editing.id, changes); setEditing(null) }}
          onDelete={() => { remove.mutate(editing.id); setEditing(null) }}
        />
      )}
      {stars > 0 && <Suspense fallback={null}><Starfall seed={stars} onDone={endStars} /></Suspense>}
      <Toast toast={toast} onClose={closeToast} />
    </div>
  )
}
