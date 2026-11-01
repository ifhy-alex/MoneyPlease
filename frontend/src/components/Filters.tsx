import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { ExploreFilters } from '../api/types'

export function filtersFromParams(p: URLSearchParams): ExploreFilters {
  const num = (k: string) => (p.get(k) ? Number(p.get(k)) : undefined)
  return {
    q: p.get('q') ?? undefined,
    source: p.get('source') ?? undefined,
    modalidad: p.get('modalidad') ?? undefined,
    solo_cr: p.get('solo_cr') === '1' || undefined,
    min_score: num('min_score'),
    fit: p.get('fit') ?? undefined,
    desde: p.get('desde') ?? undefined,
    page: num('page') ?? 1,
    sort: (p.get('sort') as ExploreFilters['sort']) ?? undefined,
  }
}

const field = 'rounded-lg border border-line bg-surface px-2 py-1.5 text-sm text-text'

/** Filtros de Explorar: viven en la URL para que se puedan guardar o compartir. */
export function Filters() {
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState(params.get('q') ?? '')

  const set = (key: string, value: string | null) =>
    setParams((prev) => {
      const next = new URLSearchParams(prev)
      if (value) next.set(key, value)
      else next.delete(key)
      if (key !== 'page') next.delete('page')
      return next
    })

  useEffect(() => {
    if (q === (params.get('q') ?? '')) return
    const id = setTimeout(() => set('q', q.trim() || null), 300)
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q])

  return (
    <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()} role="search">
      <label className="flex flex-col text-xs text-muted">
        Buscar
        <input type="search" value={q} onChange={(e) => setQ(e.target.value)} className={field}
               placeholder="Título, empresa o descripción" />
      </label>
      <label className="flex flex-col text-xs text-muted">
        Modalidad
        <select value={params.get('modalidad') ?? ''} onChange={(e) => set('modalidad', e.target.value || null)} className={field}>
          <option value="">Todas</option>
          <option value="presencial">Presencial</option>
          <option value="hibrido">Híbrido</option>
          <option value="remoto">Remoto</option>
        </select>
      </label>
      <label className="flex flex-col text-xs text-muted">
        Fuente
        <select value={params.get('source') ?? ''} onChange={(e) => set('source', e.target.value || null)} className={field}>
          <option value="">Todas</option>
          {['greenhouse', 'lever', 'workday', 'jsearch', 'gmail'].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </label>
      <label className="flex flex-col text-xs text-muted">
        Fit
        <select value={params.get('fit') ?? ''} onChange={(e) => set('fit', e.target.value || null)} className={field}>
          <option value="">Todos</option>
          <option value="practica">Práctica</option>
          <option value="junior">Junior</option>
          <option value="no_aplica">No aplica</option>
        </select>
      </label>
      <label className="flex flex-col text-xs text-muted">
        Score mínimo
        <input type="number" min={0} max={100} step={5} value={params.get('min_score') ?? ''} className={`${field} w-24`}
               onChange={(e) => set('min_score', e.target.value || null)} />
      </label>
      <label className="flex flex-col text-xs text-muted">
        Desde
        <input type="date" value={params.get('desde') ?? ''} onChange={(e) => set('desde', e.target.value || null)} className={field} />
      </label>
      <label className="flex items-center gap-2 pb-1.5 text-sm">
        <input type="checkbox" checked={params.get('solo_cr') === '1'} onChange={(e) => set('solo_cr', e.target.checked ? '1' : null)} />
        Solo Costa Rica
      </label>
      <label className="flex flex-col text-xs text-muted">
        Orden
        <select value={params.get('sort') ?? 'score'} onChange={(e) => set('sort', e.target.value === 'score' ? null : e.target.value)} className={field}>
          <option value="score">Score</option>
          <option value="fecha">Más nuevas</option>
        </select>
      </label>
    </form>
  )
}
