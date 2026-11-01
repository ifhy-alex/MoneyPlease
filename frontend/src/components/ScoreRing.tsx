import type { Fit } from '../api/types'

/** Plata para los puntajes buenos, gris para el resto: sin semáforo rojo/verde. */
export function scoreColor(score: number): string {
  return score >= 60 ? 'var(--silver)' : 'var(--muted)'
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
      <text textAnchor="middle" dominantBaseline="central" fontSize="11" fontWeight="500" fontFamily="var(--font-mono)" fill="var(--text)">
        {score}
      </text>
    </svg>
  )
}
