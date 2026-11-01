import { lazy, Suspense, useCallback, useState } from 'react'
import { errorMessage } from '../api/client'
import { useApplications, useDeleteApplication, useUpdateApplication, type ApplicationChanges } from '../api/hooks'
import type { ApplicationItem, Estado } from '../api/types'
import { burstOrigin } from '../art/burstOrigin'
import { ApplicationEditor } from '../components/ApplicationEditor'
import { Kanban } from '../components/Kanban'
import { Toast, type ToastState } from '../components/Toast'
import { EmptyState } from '../decor/EmptyState'
import { usePrefersReducedMotion } from '../lib/motion'

const Pipeline = lazy(() => import('../art/Pipeline'))
const ParticleBurst = lazy(() => import('../art/ParticleBurst'))
const CELEBRATE: Estado[] = ['entrevista', 'oferta']

export default function Applications() {
  const apps = useApplications()
  const update = useUpdateApplication()
  const remove = useDeleteApplication()
  const reduced = usePrefersReducedMotion()
  const [view, setView] = useState<'pipeline' | 'tablero'>('pipeline')
  const [editing, setEditing] = useState<ApplicationItem | null>(null)
  const [burst, setBurst] = useState(0)
  const [origin, setOrigin] = useState<{ x: number; y: number } | null>(null)
  const [toast, setToast] = useState<ToastState | null>(null)
  const closeToast = useCallback(() => setToast(null), [])
  const endBurst = useCallback(() => setBurst(0), [])

  const change = (id: number, changes: ApplicationChanges) =>
    update.mutate({ id, changes }, {
      onSuccess: () => {
        if (changes.estado && CELEBRATE.includes(changes.estado) && !reduced) {
          setOrigin(burstOrigin(id))
          setBurst(Date.now())
        }
      },
      onError: (err) => setToast({ message: errorMessage(err), tone: 'error' }),
    })

  const list = apps.data ?? []
  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <h1>Postulaciones</h1>
        <div role="tablist" aria-label="Vista" className="flex gap-1 rounded-xl border border-line p-1 text-sm">
          {(['pipeline', 'tablero'] as const).map((v) => (
            <button key={v} type="button" role="tab" aria-selected={view === v} onClick={() => setView(v)}
                    className={`rounded-lg px-3 py-1 ${view === v ? 'bg-surface text-accent' : 'text-muted'}`}>
              {v === 'pipeline' ? 'Pipeline' : 'Tablero'}
            </button>
          ))}
        </div>
      </header>
      {apps.isLoading && <p className="text-muted">Cargando…</p>}
      {apps.data && list.length === 0 && (
        <EmptyState kind="sin-postulaciones" title="Todavía no guardaste ninguna oferta."
                    text="Usa 🔖 Guardar en Inicio o Explorar para agregar la primera." />
      )}
      {list.length > 0 && (view === 'pipeline' ? (
        <Suspense fallback={null}><Pipeline apps={list} onSelect={setEditing} /></Suspense>
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
      {burst > 0 && <Suspense fallback={null}><ParticleBurst seed={burst} origin={origin} onDone={endBurst} /></Suspense>}
      <Toast toast={toast} onClose={closeToast} />
    </div>
  )
}
