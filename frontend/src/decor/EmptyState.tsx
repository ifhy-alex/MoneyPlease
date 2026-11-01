import type { ReactNode } from 'react'
import { seeded } from '../art/random'

export type EmptyKind = 'sin-ofertas' | 'sin-postulaciones' | 'sin-perfil'

/** Retícula de puntos con algunos encendidos: todavía no llegan ofertas. */
function DotGrid() {
  const rnd = seeded('sin-ofertas')
  const dots = []
  for (let y = 0; y < 8; y++) {
    for (let x = 0; x < 16; x++) {
      const v = rnd()
      dots.push(<circle key={`${x}-${y}`} cx={8 + x * 9.6} cy={10 + y * 10} r={v > 0.92 ? 1.8 : 0.9}
                        fill={v > 0.92 ? 'var(--silver)' : 'var(--glow)'} fillOpacity={v > 0.92 ? 0.9 : 0.5} />)
    }
  }
  return <svg viewBox="0 0 160 90" width="160" height="90" aria-hidden="true">{dots}</svg>
}

/** Líneas de contorno planas: todavía no hay postulaciones en movimiento. */
function Contours() {
  const rnd = seeded('sin-postulaciones')
  const lines = Array.from({ length: 9 }, (_, i) => {
    const phase = rnd() * Math.PI * 2
    const amp = 2 + i * 0.6
    const pts = Array.from({ length: 33 }, (_, k) => {
      const x = k * 5
      return `${x},${(12 + i * 8.5 + Math.sin(x / 18 + phase) * amp).toFixed(2)}`
    })
    return <polyline key={i} points={pts.join(' ')} fill="none" stroke={i === 4 ? 'var(--silver)' : 'var(--glow)'}
                     strokeOpacity={i === 4 ? 0.8 : 0.45} strokeWidth={0.8} />
  })
  return <svg viewBox="0 0 160 90" width="160" height="90" aria-hidden="true">{lines}</svg>
}

/** Mosaico de Truchet: el patrón espera los datos del perfil. */
function Truchet() {
  const rnd = seeded('sin-perfil')
  const size = 10
  const tiles = []
  for (let y = 0; y < 9; y++) {
    for (let x = 0; x < 16; x++) {
      const ox = x * size
      const oy = y * size
      const d = rnd() > 0.5
        ? `M${ox + 5},${oy} A5,5 0 0 1 ${ox},${oy + 5} M${ox + 10},${oy + 5} A5,5 0 0 0 ${ox + 5},${oy + 10}`
        : `M${ox + 5},${oy} A5,5 0 0 0 ${ox + 10},${oy + 5} M${ox},${oy + 5} A5,5 0 0 1 ${ox + 5},${oy + 10}`
      tiles.push(<path key={`${x}-${y}`} d={d} fill="none" stroke="var(--glow)" strokeOpacity={0.55} strokeWidth={0.9} />)
    }
  }
  return <svg viewBox="0 0 160 90" width="160" height="90" aria-hidden="true">{tiles}</svg>
}

const ART: Record<EmptyKind, () => ReactNode> = { 'sin-ofertas': DotGrid, 'sin-postulaciones': Contours, 'sin-perfil': Truchet }

export function EmptyState({ kind, title, text, children }: { kind: EmptyKind; title: string; text?: string; children?: ReactNode }) {
  const Art = ART[kind]
  return (
    <div className="flex flex-col items-center gap-2 glass p-6 text-center">
      <Art />
      <p className="font-semibold text-lg">{title}</p>
      {text && <p className="text-sm text-muted">{text}</p>}
      {children}
    </div>
  )
}
