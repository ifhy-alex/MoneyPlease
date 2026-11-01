import { useLayoutEffect, useRef, useState } from 'react'
import type { ApplicationItem } from '../api/types'
import { columnX, layoutPipeline, sideX, STAGES } from './pipelineLayout'

const H = 280
const LABEL: Record<string, string> = { guardada: 'guardada', aplicada: 'aplicada', entrevista: 'entrevista', oferta: 'oferta' }

/** Pipeline de postulaciones: cada una es un nodo que avanza por las etapas; los caminos muestran por dónde pasó. */
export default function Pipeline({ apps, onSelect }: { apps: ApplicationItem[]; onSelect: (a: ApplicationItem) => void }) {
  const ref = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(600)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const update = () => setWidth(el.clientWidth || 600)
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  const top = 28
  const { nodes, paths } = layoutPipeline(apps, width, H - top)
  const byId = new Map(apps.map((a) => [a.id, a]))
  return (
    <div ref={ref} className="glass relative overflow-hidden" style={{ height: H }}>
      <svg aria-hidden="true" width="100%" height={H} className="absolute inset-0">
        {STAGES.map((s, i) => (
          <g key={s}>
            <line x1={columnX(i, width)} x2={columnX(i, width)} y1={top} y2={H - 8} stroke="var(--line)" strokeDasharray="2 4" />
            <text x={columnX(i, width)} y={16} textAnchor="middle" fontSize={10} fontFamily="var(--font-mono)" fill="var(--muted)">
              {LABEL[s]}
            </text>
          </g>
        ))}
        <line x1={width * 0.82} x2={width * 0.82} y1={8} y2={H - 8} stroke="var(--line)" />
        <text x={sideX(width)} y={16} textAnchor="middle" fontSize={10} fontFamily="var(--font-mono)" fill="var(--muted)">
          descartada
        </text>
        <g transform={`translate(0 ${top})`}>
          {paths.map((p) => {
            const rejected = byId.get(p.id)?.estado === 'rechazada'
            return <path key={p.id} d={p.d} fill="none" stroke={rejected ? 'var(--danger)' : 'var(--line-strong)'}
                         strokeOpacity={rejected ? 0.35 : 1} strokeWidth={1} />
          })}
        </g>
      </svg>
      {nodes.map((n) => {
        const app = byId.get(n.id)!
        const rejected = n.estado === 'rechazada'
        return (
          <button key={n.id} type="button" onClick={() => onSelect(app)} aria-label={`Editar ${n.titulo}`}
                  title={`${n.titulo} — ${app.job.empresa} (${n.estado})`}
                  className="group absolute flex h-6 w-6 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full"
                  style={{ left: n.x, top: n.y + top }}>
            {n.seguimiento && (
              <span aria-hidden="true" className="absolute inset-0 animate-ping rounded-full border border-silver/60" />
            )}
            <span aria-hidden="true"
                  className={`block h-3 w-3 rounded-full border transition-transform group-hover:scale-150 ${
                    rejected ? 'border-danger/70 bg-bg' : 'border-silver bg-silver/80'}`} />
          </button>
        )
      })}
    </div>
  )
}
