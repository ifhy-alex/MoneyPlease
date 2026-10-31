import { useEffect, useState, type ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { useInsights } from '../api/hooks'
import type { Theme } from '../lib/tokens'

const LINKS = [
  { to: '/', label: 'Inicio', icon: '✦' },
  { to: '/explorar', label: 'Explorar', icon: '⌕' },
  { to: '/postulaciones', label: 'Postulaciones', icon: '❀' },
  { to: '/perfil', label: 'Perfil', icon: '☾' },
]

function initialTheme(): Theme {
  const saved = localStorage.getItem('theme')
  if (saved === 'dark' || saved === 'light') return saved
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(initialTheme)
  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])
  const toggle = () =>
    setTheme((t) => {
      const next = t === 'dark' ? 'light' : 'dark'
      localStorage.setItem('theme', next)
      return next
    })
  return [theme, toggle]
}

function NavItems({ compact }: { compact?: boolean }) {
  return (
    <>
      {LINKS.map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          end={l.to === '/'}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors ${
              compact ? 'flex-col gap-0.5 text-xs' : ''
            } ${isActive ? 'bg-surface text-accent' : 'text-muted hover:text-text'}`
          }
        >
          <span aria-hidden="true" className="text-lg leading-none">{l.icon}</span>
          {l.label}
        </NavLink>
      ))}
    </>
  )
}

export function Layout({ children, background }: { children: ReactNode; background?: ReactNode }) {
  const [theme, toggle] = useTheme()
  const insights = useInsights()
  return (
    <div className="relative min-h-screen bg-bg text-text">
      {background}
      {insights.data?.demo && (
        <div role="status" className="relative z-10 bg-accent px-4 py-1 text-center text-sm font-medium text-bg">
          Modo demo: datos ficticios
        </div>
      )}
      <div className="relative z-10 mx-auto flex max-w-7xl">
        <aside className="sticky top-0 hidden h-screen w-56 shrink-0 flex-col gap-1 p-4 md:flex">
          <p className="mb-6 px-3 font-display text-xl">MoneyPlease</p>
          <nav aria-label="Secciones" className="flex flex-col gap-1">
            <NavItems />
          </nav>
          <button
            type="button"
            onClick={toggle}
            aria-label={`Cambiar tema (actual: ${theme === 'dark' ? 'oscuro' : 'claro'})`}
            className="mt-auto rounded-xl px-3 py-2 text-left text-sm text-muted hover:text-text"
          >
            {theme === 'dark' ? '☀ Tema claro' : '☾ Tema oscuro'}
          </button>
        </aside>
        <main className="min-w-0 flex-1 px-4 pb-24 pt-6 md:px-8 md:pb-8">{children}</main>
      </div>
      <nav
        aria-label="Secciones (móvil)"
        className="fixed inset-x-0 bottom-0 z-20 flex justify-around border-t border-line bg-surface/95 p-2 backdrop-blur md:hidden"
      >
        <NavItems compact />
      </nav>
    </div>
  )
}
