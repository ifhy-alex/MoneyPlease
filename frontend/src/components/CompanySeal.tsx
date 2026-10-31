import { polygonPoints, sealParams } from '../art/seal'

export function CompanySeal({ company, size = 40 }: { company: string; size?: number }) {
  const p = sealParams(company)
  const color = `hsl(${p.hue} 65% 60%)`
  return (
    <svg width={size} height={size} viewBox="-20 -20 40 40" aria-hidden="true" className="shrink-0">
      <circle r="19" fill="var(--surface)" stroke="var(--line)" />
      {Array.from({ length: p.rings }, (_, i) => (
        <polygon
          key={i}
          points={polygonPoints(p.sides, 15 - i * 4.5, p.rotation + i * 17)}
          fill={i === p.rings - 1 ? color : 'none'}
          fillOpacity={0.35}
          stroke={color}
          strokeWidth={1.2}
        />
      ))}
    </svg>
  )
}
