import type { ReactNode } from 'react'

export type EmptyKind = 'sin-ofertas' | 'sin-postulaciones' | 'sin-perfil'

/** Luna sobre colinas: no hay ofertas nuevas hoy. */
function Moon() {
  return (
    <svg viewBox="0 0 160 90" width="160" height="90" aria-hidden="true">
      <circle cx="112" cy="28" r="14" fill="var(--accent)" />
      <circle cx="118" cy="24" r="12" fill="var(--surface)" />
      {[[20, 18], [46, 30], [70, 12], [140, 50]].map(([x, y]) => <circle key={`${x}`} cx={x} cy={y} r="1.3" fill="var(--accent)" />)}
      <path d="M0 80 Q 40 52 80 72 T 160 66 V90 H0Z" fill="var(--muted)" fillOpacity="0.25" />
      <path d="M0 86 Q 50 66 100 82 T 160 80 V90 H0Z" fill="var(--muted)" fillOpacity="0.4" />
    </svg>
  )
}

/** Semilla en la tierra: todavía no hay postulaciones. */
function Seed() {
  return (
    <svg viewBox="0 0 160 90" width="160" height="90" aria-hidden="true">
      <path d="M20 70 H140" stroke="var(--muted)" strokeOpacity="0.5" />
      <ellipse cx="80" cy="66" rx="9" ry="6" fill="var(--accent)" />
      <path d="M80 60 C 78 48, 84 42, 80 34" stroke="var(--ok)" strokeWidth="2" fill="none" strokeDasharray="3 3" />
      <circle cx="80" cy="30" r="2" fill="var(--ok)" />
    </svg>
  )
}

/** Constelación sin estrellas encendidas: falta el perfil. */
function EmptyConstellation() {
  const pts = [[30, 60], [60, 30], [95, 45], [125, 20], [140, 62]]
  return (
    <svg viewBox="0 0 160 90" width="160" height="90" aria-hidden="true">
      <polyline points={pts.map((p) => p.join(',')).join(' ')} fill="none" stroke="var(--muted)" strokeOpacity="0.35" strokeDasharray="2 4" />
      {pts.map(([x, y]) => <circle key={`${x}`} cx={x} cy={y} r="3" fill="none" stroke="var(--accent)" />)}
    </svg>
  )
}

const ART: Record<EmptyKind, () => ReactNode> = { 'sin-ofertas': Moon, 'sin-postulaciones': Seed, 'sin-perfil': EmptyConstellation }

export function EmptyState({ kind, title, text, children }: { kind: EmptyKind; title: string; text?: string; children?: ReactNode }) {
  const Art = ART[kind]
  return (
    <div className="flex flex-col items-center gap-2 rounded-[var(--radius-card)] border border-line bg-surface p-6 text-center">
      <Art />
      <p className="font-display text-lg">{title}</p>
      {text && <p className="text-sm text-muted">{text}</p>}
      {children}
    </div>
  )
}
