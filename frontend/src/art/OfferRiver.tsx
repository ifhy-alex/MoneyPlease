import { area, curveBasis, scaleLinear, stack, stackOffsetWiggle, stackOrderInsideOut } from 'd3'
import { useMemo } from 'react'
import { useFlow } from '../api/hooks'
import { SOURCE_COLORS, toSeries } from './river'

const W = 600
const H = 120

/** Streamgraph de ofertas nuevas por tipo de fuente y semana. */
export default function OfferRiver() {
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
    const y = scaleLinear().domain([lo, hi === lo ? lo + 1 : hi]).range([H, 0])
    const path = area<[number, number]>().x((_, i) => x(i)).y0((d) => y(d[0])).y1((d) => y(d[1])).curve(curveBasis)
    return stacked.map((layer, i) => ({ d: path(layer as unknown as [number, number][]) ?? '', i }))
  }, [series])

  if (layers.length === 0) {
    return <p className="text-sm text-muted">El río de ofertas aparece cuando haya al menos dos semanas de datos.</p>
  }
  return (
    <figure className="flex flex-col gap-2">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-28 w-full" role="img"
           aria-label="Ofertas nuevas por fuente en las últimas semanas" preserveAspectRatio="none">
        {layers.map(({ d, i }) => (
          <path key={series.fuentes[i]} d={d} fill={SOURCE_COLORS[i % SOURCE_COLORS.length]} fillOpacity={0.75}>
            <title>{`${series.fuentes[i]}: ${series.matrix.reduce((s, r) => s + r[i], 0)} ofertas`}</title>
          </path>
        ))}
      </svg>
      <figcaption className="flex flex-wrap gap-3 text-xs text-muted">
        {series.fuentes.map((f, i) => (
          <span key={f} className="flex items-center gap-1">
            <span aria-hidden="true" className="inline-block h-2 w-2 rounded-full"
                  style={{ background: SOURCE_COLORS[i % SOURCE_COLORS.length] }} />
            {f}
          </span>
        ))}
      </figcaption>
    </figure>
  )
}
