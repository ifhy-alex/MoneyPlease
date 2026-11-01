import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ApiError, errorMessage } from '../api/client'
import { useCreateApplication, useFeedback, useUniverse } from '../api/hooks'
import type { UniversePoint } from '../api/types'
import { JobDetail } from '../components/JobDetail'
import { Toast, type ToastState } from '../components/Toast'
import { EmptyState } from '../decor/EmptyState'
import { usePrefersReducedMotion } from '../lib/motion'
import { Panel } from '../universe/Panel'
import { createScene, NoWebGL, type SceneHandle } from '../universe/scene'
import { offerStars, scaled, topLinks3d, type Filters } from '../universe/stars'

type Vista = 'ofertas' | 'habilidades'
const ALL: Filters = { minScore: 0, empresa: null, fit: 'todas' }

/** Universo 3D: la galaxia de ofertas y el grafo de habilidades, a pantalla completa. */
export default function Universe() {
  const [params, setParams] = useSearchParams()
  const vista: Vista = params.get('vista') === 'habilidades' ? 'habilidades' : 'ofertas'
  const reduced = usePrefersReducedMotion()
  const container = useRef<HTMLDivElement>(null)
  const [scene, setScene] = useState<SceneHandle | null>(null)
  const [noWebGL, setNoWebGL] = useState(false)
  const [tooltip, setTooltip] = useState<{ id: string; x: number; y: number } | null>(null)
  const [open, setOpen] = useState<number | null>(null)
  const [toast, setToast] = useState<ToastState | null>(null)
  const closeToast = useCallback(() => setToast(null), [])
  const feedback = useFeedback()
  const save = useCreateApplication()

  useEffect(() => {
    if (!container.current) return
    let handle: SceneHandle
    try {
      handle = createScene(container.current, { reducedMotion: reduced })
    } catch (err) {
      if (err instanceof NoWebGL) {
        setNoWebGL(true)
        return
      }
      throw err
    }
    handle.onHover((id, at) => setTooltip(id ? { id, ...at } : null))
    handle.onPick((id) => { if (id.startsWith('o:')) setOpen(Number(id.slice(2))) })
    setScene(handle)
    return () => {
      handle.dispose()
      setScene(null)
    }
  }, [reduced])

  const setVista = (v: Vista) => setParams(v === 'ofertas' ? {} : { vista: v })

  return (
    <div className="fixed inset-0 z-[25] bg-bg">
      <div ref={container} className="absolute inset-0" />
      <div className="pointer-events-none absolute inset-0 flex flex-col gap-3 p-4">
        <header className="pointer-events-auto flex flex-wrap items-center gap-3">
          <Link to="/" className="mono rounded-lg border border-line bg-bg/60 px-3 py-1.5 text-xs text-silver">← Volver</Link>
          <div role="tablist" aria-label="Universo" className="flex gap-1 rounded-xl border border-line bg-bg/60 p-1 text-sm">
            {(['ofertas', 'habilidades'] as const).map((v) => (
              <button key={v} type="button" role="tab" aria-selected={vista === v} onClick={() => setVista(v)}
                      className={`rounded-lg px-3 py-1 ${vista === v ? 'bg-surface-strong text-silver' : 'text-muted'}`}>
                {v === 'ofertas' ? 'Ofertas' : 'Habilidades'}
              </button>
            ))}
          </div>
        </header>
        {noWebGL ? (
          <div className="pointer-events-auto m-auto max-w-sm text-center">
            <EmptyState kind="sin-ofertas" title="Tu navegador no puede mostrar el universo 3D."
                        text="Necesita WebGL. El mapa de Inicio muestra lo mismo en 2D.">
              <Link to="/" className="text-silver underline">Volver a Inicio</Link>
            </EmptyState>
          </div>
        ) : vista === 'ofertas' ? (
          <Offers scene={scene} />
        ) : null}
      </div>
      {tooltip && <StarTooltip id={tooltip.id} x={tooltip.x} y={tooltip.y} />}
      {open !== null && (
        <JobDetail id={open} onClose={() => setOpen(null)}
                   onFeedback={(valor) => feedback.mutate({ jobId: open, valor }, {
                     onError: (err) => setToast({ message: errorMessage(err), tone: 'error' }),
                   })}
                   onSave={() => save.mutate(open, {
                     onSuccess: () => setToast({ message: 'Guardada en postulaciones' }),
                     onError: (err) => !(err instanceof ApiError && err.status === 409) && setToast({ message: errorMessage(err), tone: 'error' }),
                   })} />
      )}
      <Toast toast={toast} onClose={closeToast} />
    </div>
  )
}

// Los textos del tooltip salen de la última respuesta del universo (la consulta ya está en caché).
function StarTooltip({ id, x, y }: { id: string; x: number; y: number }) {
  const universe = useUniverse()
  const p = universe.data?.puntos.find((q) => `o:${q.job_id}` === id)
  if (!p) return null
  return (
    <div role="tooltip" className="glass panel pointer-events-none fixed z-[26] max-w-64 px-3 py-2 text-xs"
         style={{ left: Math.max(8, Math.min(x + 14, window.innerWidth - 270)), top: Math.max(8, y - 10) }}>
      <p className="font-medium text-text">{p.titulo}</p>
      <p className="text-muted">{p.empresa}</p>
      <p className="mono mt-1 text-silver">{p.puntaje === null ? 'sin evaluar' : `${p.puntaje} / 100`}</p>
    </div>
  )
}

function Offers({ scene }: { scene: SceneHandle | null }) {
  const universe = useUniverse()
  const [filters, setFilters] = useState<Filters>(ALL)
  const puntos = useMemo(() => universe.data?.puntos ?? [], [universe.data])
  const nubes = useMemo(() => universe.data?.nubes ?? [], [universe.data])
  const empresas = useMemo(() => [...new Set(puntos.map((p) => p.empresa))].sort(), [puntos])

  useEffect(() => {
    if (!scene) return
    scene.setCenter(true)
    scene.setStars(offerStars(puntos, filters))
    scene.setLinks(topLinks3d(puntos).map((p) => [[0, 0, 0], p]))
    scene.setLabels(nubes.map((n) => ({ pos: scaled(n), text: `${n.nombre} · ${n.n}`, color: '#7A8399' })))
  }, [scene, puntos, nubes, filters])

  const byId = useMemo(() => new Map<string, UniversePoint>(puntos.map((p) => [`o:${p.job_id}`, p])), [puntos])
  const items = useMemo(() => puntos.map((p) => ({ id: `o:${p.job_id}`, text: `${p.titulo} · ${p.empresa}` })), [puntos])

  if (universe.isError) {
    if (universe.error instanceof ApiError && universe.error.status === 404) {
      return (
        <div className="pointer-events-auto m-auto max-w-sm">
          <EmptyState kind="sin-perfil" title="Guarda tu perfil para ver el universo.">
            <Link to="/perfil" className="text-silver underline">Ir a Perfil</Link>
          </EmptyState>
        </div>
      )
    }
    return (
      <div role="alert" className="glass panel pointer-events-auto m-auto flex flex-col items-center gap-3 p-6 text-sm">
        <p className="text-muted">{errorMessage(universe.error)}</p>
        <button type="button" onClick={() => universe.refetch()} className="rounded-lg border border-line px-3 py-1.5 text-silver">
          Reintentar
        </button>
      </div>
    )
  }
  if (universe.isPending) return <p className="mono pointer-events-auto text-xs text-muted">Cargando el universo…</p>
  if (puntos.length === 0) {
    return <p className="pointer-events-auto m-auto text-sm text-muted">Todavía no hay ofertas para mostrar en el universo.</p>
  }
  return (
    <Panel items={items} onChoose={(id) => { const p = byId.get(id); if (p) scene?.flyTo(scaled(p)) }}>
      <label className="flex flex-col gap-1 text-xs text-muted">
        Puntaje mínimo: <span className="mono text-silver">{filters.minScore}</span>
        <input type="range" min={0} max={100} step={5} value={filters.minScore} aria-label="Puntaje mínimo"
               onChange={(e) => setFilters((f) => ({ ...f, minScore: Number(e.target.value) }))} />
      </label>
      <label className="flex flex-col gap-1 text-xs text-muted">
        Empresa
        <select value={filters.empresa ?? ''} onChange={(e) => setFilters((f) => ({ ...f, empresa: e.target.value || null }))}
                className="rounded-lg border border-line bg-bg/60 px-2 py-1.5 text-sm text-text">
          <option value="">Todas</option>
          {empresas.map((e) => <option key={e} value={e}>{e}</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs text-muted">
        Tipo
        <select value={filters.fit} onChange={(e) => setFilters((f) => ({ ...f, fit: e.target.value as Filters['fit'] }))}
                className="rounded-lg border border-line bg-bg/60 px-2 py-1.5 text-sm text-text">
          <option value="todas">Todas</option>
          <option value="practica">Práctica</option>
          <option value="junior">Junior</option>
        </select>
      </label>
      <ul aria-label="Nubes" className="flex flex-col gap-1">
        {nubes.map((n) => (
          <li key={n.id}>
            <button type="button" onClick={() => scene?.flyTo(scaled(n))}
                    className="flex w-full justify-between rounded-md px-2 py-1 text-left text-sm hover:bg-surface-strong">
              <span className="truncate">{n.nombre}</span>
              <span className="mono text-muted">{n.n}</span>
            </button>
          </li>
        ))}
      </ul>
      <p className="mono text-[11px] text-muted">Arrastra para rotar · rueda o pellizco para acercar · clic para abrir</p>
    </Panel>
  )
}

