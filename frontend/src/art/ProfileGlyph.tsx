import type { ProfileVersion } from '../api/types'
import { AREAS, glyphPoints, normalizeAreas } from './glyph'

/** Huella del perfil: un glifo radial por versión; la más nueva opaca y las anteriores superpuestas. */
export default function ProfileGlyph({ versions }: { versions: ProfileVersion[] }) {
  const R = 70
  const axes = normalizeAreas(versions)
  if (axes.length === 0) return null
  return (
    <svg viewBox="-110 -100 220 200" className="w-full max-w-xs" role="img"
         aria-label={`Huella de ${versions.length} versiones del perfil por área de habilidades`}>
      {[0.33, 0.66, 1].map((k) => (
        <polygon key={k} points={glyphPoints(AREAS.map(() => k), R)} fill="none" stroke="var(--line)" />
      ))}
      {AREAS.map((a, i) => {
        const ang = -Math.PI / 2 + (i * 2 * Math.PI) / AREAS.length
        return (
          <text key={a} x={Math.cos(ang) * (R + 16)} y={Math.sin(ang) * (R + 16)} fontSize={9}
                textAnchor="middle" dominantBaseline="central" fill="var(--muted)">{a}</text>
        )
      })}
      {[...axes].reverse().map((ax, i, all) => {
        const newest = i === all.length - 1
        return (
          <polygon key={versions[all.length - 1 - i].version} points={glyphPoints(ax, R)}
                   fill="var(--accent)" fillOpacity={newest ? 0.35 : 0.08}
                   stroke="var(--accent)" strokeOpacity={newest ? 1 : 0.25} />
        )
      })}
    </svg>
  )
}
