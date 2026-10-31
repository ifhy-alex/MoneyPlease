import { useSkills } from '../api/hooks'
import { starLayout } from './constellationLayout'

/** Constelación de habilidades a partir de las evaluaciones del perfil activo. */
export default function Constellation({ compact = false }: { compact?: boolean }) {
  const skills = useSkills()
  const w = compact ? 260 : 520
  const h = compact ? 160 : 320
  const stars = starLayout(skills.data ?? [], w, h)
  if (stars.length === 0) return <p className="text-sm text-muted">La constelación aparece cuando haya ofertas evaluadas.</p>
  const byArea = new Map<string, typeof stars>()
  for (const s of stars) byArea.set(s.area, [...(byArea.get(s.area) ?? []), s])
  return (
    <figure className="flex flex-col gap-1">
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full" role="img"
           aria-label={`Constelación de ${stars.length} habilidades; en coral, las brechas que no tienes`}>
        {[...byArea.values()].map((group) =>
          group.slice(1).map((s, i) => (
            <line key={`${s.skill}-l`} x1={group[i].x} y1={group[i].y} x2={s.x} y2={s.y}
                  stroke="var(--muted)" strokeOpacity={0.18} />
          )))}
        {stars.map((s) => (
          <g key={s.skill}>
            <circle cx={s.x} cy={s.y} r={s.r} fill={s.color} fillOpacity={s.opacity}>
              <title>{s.skill}</title>
            </circle>
            {!compact && s.r > 3.5 && (
              <text x={s.x + s.r + 3} y={s.y + 3} fontSize={10} fill="var(--muted)">{s.skill}</text>
            )}
          </g>
        ))}
      </svg>
      {!compact && <figcaption className="text-xs text-muted">Más cerca del centro = más pedida. Opaca = ya la tienes.</figcaption>}
    </figure>
  )
}
