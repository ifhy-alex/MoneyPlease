import { useState, type ReactNode } from 'react'
import { search } from './search'

interface Props {
  items: { id: string; text: string }[]
  onChoose: (id: string) => void
  children: ReactNode
}

/** Panel de exploración: buscador con resultados y, debajo, lo propio de cada pestaña. Plegable en el celular. */
export function Panel({ items, onChoose, children }: Props) {
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(true)
  const results = search(q, items)
  const choose = (id: string) => {
    onChoose(id)
    setQ('')
  }
  return (
    <aside className="glass panel pointer-events-auto flex max-h-[70vh] w-full flex-col gap-3 overflow-y-auto p-4 sm:w-72">
      <button type="button" className="mono self-end text-[11px] text-muted sm:hidden" aria-expanded={open}
              onClick={() => setOpen((o) => !o)}>
        {open ? 'Ocultar panel ▾' : 'Mostrar panel ▴'}
      </button>
      <div className={open ? 'flex flex-col gap-3' : 'hidden sm:flex sm:flex-col sm:gap-3'}>
        <label className="flex flex-col gap-1 text-xs text-muted">
          Buscar
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="HPE, Data, Docker…"
                 onKeyDown={(e) => { if (e.key === 'Enter' && results[0]) choose(results[0].id) }}
                 className="rounded-lg border border-line bg-bg/60 px-2 py-1.5 text-sm text-text" />
        </label>
        {results.length > 0 && (
          <ul aria-label="Resultados" className="flex flex-col gap-1">
            {results.map((r) => (
              <li key={r.id}>
                <button type="button" onClick={() => choose(r.id)}
                        className="w-full truncate rounded-md px-2 py-1 text-left text-sm hover:bg-surface-strong">
                  {r.text}
                </button>
              </li>
            ))}
          </ul>
        )}
        {children}
      </div>
    </aside>
  )
}
