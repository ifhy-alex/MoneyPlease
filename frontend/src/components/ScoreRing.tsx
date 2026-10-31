import type { Fit } from '../api/types'

export function scoreColor(score: number): string {
  if (score >= 70) return 'var(--accent)'
  if (score >= 50) return 'color-mix(in srgb, var(--accent) 55%, var(--danger))'
  return 'var(--danger)'
}

/** Arco SVG de 0 a `fraction` de la circunferencia, empezando arriba. */
export function arcPath(fraction: number, r: number): string {
  const f = Math.min(Math.max(fraction, 0), 0.9999)
  if (f === 0) return ''
  const a = f * 2 * Math.PI - Math.PI / 2
  const x = (r * Math.cos(a)).toFixed(3)
  const y = (r * Math.sin(a)).toFixed(3)
  return `M 0 ${-r} A ${r} ${r} 0 ${f > 0.5 ? 1 : 0} 1 ${x} ${y}`
}

/** Anillo de score: el arco crece con el score; las prácticas se dibujan con trazo de estrellas (punteado). */
export function ScoreRing({ score, fit, size = 48 }: { score: number; fit: Fit; size?: number }) {
  const r = 16
  return (
    <svg width={size} height={size} viewBox="-20 -20 40 40" role="img" aria-label={`Score ${score} de 100`}>
      <circle r={r} fill="none" stroke="var(--line)" strokeWidth={3} />
      <path
        d={arcPath(score / 100, r)}
        fill="none"
        stroke={scoreColor(score)}
        strokeWidth={3}
        strokeLinecap="round"
        {...(fit === 'practica' ? { strokeDasharray: '0.5 4' } : {})}
      />
      <text textAnchor="middle" dominantBaseline="central" fontSize="11" fontWeight="600" fill="var(--text)">
        {score}
      </text>
    </svg>
  )
}
