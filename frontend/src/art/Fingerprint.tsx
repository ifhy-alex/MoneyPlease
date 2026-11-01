import type { ProfileVersion } from '../api/types'
import { AREAS, fingerprintPaths, normalizeAreas } from './glyph'

/** Huella generativa del perfil: la versión activa en plata y la anterior, tenue, debajo. */
export default function Fingerprint({ versions }: { versions: ProfileVersion[] }) {
  const R = 70
  const axes = normalizeAreas(versions)
  if (axes.length === 0) return null
  const [current, previous] = axes
  return (
    <svg viewBox="-100 -100 200 200" width={160} height={160} role="img"
         aria-label={`Huella de ${versions.length} versiones del perfil por área de habilidades`}>
      {previous && fingerprintPaths(previous, R, `v${versions[1].version}`).map((d, i) => (
        <path key={`p${i}`} d={d} fill="none" stroke="var(--glow)" strokeOpacity={0.5} strokeWidth={1} />
      ))}
      {fingerprintPaths(current, R, `v${versions[0].version}`).map((d, i) => (
        <path key={`c${i}`} d={d} fill="none" stroke="var(--silver)" strokeWidth={1.4} strokeLinecap="round" />
      ))}
      <circle r={3} fill="var(--text)" />
      {AREAS.map((a, i) => {
        const ang = -Math.PI / 2 + ((i + 0.5) * 2 * Math.PI) / AREAS.length
        return (
          <text key={a} x={Math.cos(ang) * (R + 18)} y={Math.sin(ang) * (R + 18)} fontSize={8}
                fontFamily="var(--font-mono)" textAnchor="middle" dominantBaseline="central" fill="var(--muted)">{a}</text>
        )
      })}
    </svg>
  )
}
