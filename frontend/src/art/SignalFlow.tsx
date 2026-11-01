import { area, curveBasis, scaleLinear, stack, stackOffsetWiggle, stackOrderInsideOut } from 'd3'
import { useMemo } from 'react'
import { useFlow } from '../api/hooks'
import { ArtFrame } from './ArtFrame'
import { SOURCE_COLORS, toSeries } from './river'

const W = 600
const H = 120

/** Flujo de ingesta: ofertas nuevas por fuente y semana, dibujado como un monitor de señales. */
export default function SignalFlow() {
  const flow = useFlow()
  const series = useMemo(() => toSeries(flow.data ?? []), [flow.data])
  const layers = useMemo(() => {
    if (series.semanas.length < 2 || series.fuentes.length === 0) return []
    const rows = series.matrix.map((r) => Object.fromEntries(r.map((v, i) => [series.fuentes[i], v])))
    const stacked = stack<Record<string, number>>()
      .keys(series.fuentes)
      .offset(stackOffsetWiggle)
      .order(stackOrderInsideOut)(rows)
    const lo = Math.min(...stacked.flatMap((l) => l.map((d) => d[0])))
    const hi = Math.max(...stacked.flatMap((l) => l.map((d) => d[1])))
    const x = scaleLinear().domain([0, series.semanas.length - 1]).range([0, W])
    const y = scaleLinear().domain([lo, hi === lo ? lo + 1 : hi]).range([H - 4, 4])
    const path = area<[number, number]>().x((_, i) => x(i)).y0((d) => y(d[0])).y1((d) => y(d[1])).curve(curveBasis)
    return stacked.map((layer, i) => ({ d: path(layer as unknown as [number, number][]) ?? '', i }))
  }, [series])

  return (
    <ArtFrame query={flow} height={H + 40} empty={false} emptyTitle="">
      {layers.length === 0 ? (
        <p className="mono text-xs text-muted">El flujo de ofertas aparece cuando haya al menos dos semanas de datos.</p>
      ) : (
        <figure className="glass flex flex-col gap-2 p-3">
          <svg viewBox={`0 0 ${W} ${H}`} className="h-28 w-full" role="img"
               aria-label="Flujo de ofertas nuevas por fuente en las últimas semanas" preserveAspectRatio="none">
            {[0.2, 0.4, 0.6, 0.8].map((k) => (
              <line key={k} x1={0} x2={W} y1={H * k} y2={H * k} stroke="var(--line)" vectorEffect="non-scaling-stroke" />
            ))}
            {layers.map(({ d, i }) => {
              const color = SOURCE_COLORS[i % SOURCE_COLORS.length]
              return (
                <path key={series.fuentes[i]} d={d} fill={color} fillOpacity={0.08} stroke={color} strokeWidth={1}
                      vectorEffect="non-scaling-stroke">
                  <title>{`${series.fuentes[i]}: ${series.matrix.reduce((s, r) => s + r[i], 0)} ofertas`}</title>
                </path>
              )
            })}
          </svg>
          <figcaption className="mono flex flex-wrap items-center gap-3 text-[11px] text-muted">
            <span>{series.semanas[0]} → {series.semanas.at(-1)}</span>
            {series.fuentes.map((f, i) => (
              <span key={f} className="flex items-center gap-1">
                <span aria-hidden="true" className="inline-block h-px w-3"
                      style={{ background: SOURCE_COLORS[i % SOURCE_COLORS.length] }} />
                {f}
              </span>
            ))}
          </figcaption>
        </figure>
      )}
    </ArtFrame>
  )
}
