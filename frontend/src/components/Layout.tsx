import type { ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useInsights } from '../api/hooks'
import { TOP_SCORE } from '../lib/top'

const LINKS = [
  { to: '/', label: 'Inicio', icon: '◈' },
  { to: '/explorar', label: 'Explorar', icon: '⌕' },
  { to: `/explorar?min_score=${TOP_SCORE}`, label: `Mejores (${TOP_SCORE}+)`, icon: '★' },
  { to: '/postulaciones', label: 'Postulaciones', icon: '⋯' },
  { to: '/perfil', label: 'Perfil', icon: '◎' },
]

function NavItems({ compact }: { compact?: boolean }) {
  const { search } = useLocation()
  // NavLink ignora la query: "Mejores" y "Explorar" comparten ruta y se distinguen por min_score.
  const best = new URLSearchParams(search).get('min_score') === String(TOP_SCORE)
  return (
    <>
      {LINKS.map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          end={l.to === '/'}
          className={({ isActive }) => {
            const active = isActive && (!l.to.startsWith('/explorar') || l.to.includes('min_score') === best)
            return `flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors ${
              compact ? 'flex-col gap-0.5 text-xs' : ''
            } ${active ? 'bg-surface text-accent' : 'text-muted hover:text-text'}`
          }}
        >
          <span aria-hidden="true" className="text-lg leading-none">{l.icon}</span>
          {l.label}
        </NavLink>
      ))}
    </>
  )
}

export function Layout({ children, background }: { children: ReactNode; background?: ReactNode }) {
  const insights = useInsights()
  return (
    <div className="relative min-h-screen bg-bg text-text">
      {background}
      {insights.data?.demo && (
        <div role="status" className="relative z-10 mono border-b border-line bg-glow/30 px-4 py-1 text-center text-xs tracking-wide text-silver">
          Modo demo: datos ficticios
        </div>
      )}
      <div className="relative z-10 mx-auto flex max-w-7xl">
        <aside className="sticky top-0 hidden h-screen w-56 shrink-0 flex-col gap-1 p-4 md:flex">
          <p className="mb-6 px-3 text-lg font-semibold tracking-tight">MoneyPlease</p>
          <nav aria-label="Secciones" className="flex flex-col gap-1">
            <NavItems />
          </nav>
        </aside>
        <main className="min-w-0 flex-1 px-4 pb-24 pt-6 md:px-8 md:pb-8">{children}</main>
      </div>
      <nav
        aria-label="Secciones (móvil)"
        className="fixed inset-x-0 bottom-0 z-20 flex justify-around border-t border-line bg-bg/80 p-2 backdrop-blur-xl md:hidden"
      >
        <NavItems compact />
      </nav>
    </div>
  )
}
