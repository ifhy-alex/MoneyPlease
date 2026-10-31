import { useLayoutEffect, useRef, useState } from 'react'
import type { ApplicationItem } from '../api/types'
import { plantLayout, type Stage } from './gardenLayout'
import { sealParams } from './seal'

const H = 260

function PlantShape({ stage, hue }: { stage: Stage; hue: number }) {
  const stem = 'var(--ok)'
  if (stage === 'wilted') {
    return (
      <g transform="rotate(25 0 0)" opacity={0.55}>
        <path d="M0 0 C 2 -14, -3 -24, 4 -32" stroke="var(--muted)" strokeWidth={2} fill="none" />
        <circle cx={5} cy={-33} r={4} fill="var(--muted)" />
      </g>
    )
  }
  if (stage === 0) return <ellipse cx={0} cy={-3} rx={5} ry={3.5} fill="var(--accent)" opacity={0.85} />
  const height = [0, 18, 32, 40][stage]
  return (
    <g>
      <path d={`M0 0 C 2 ${-height / 3}, -2 ${(-2 * height) / 3}, 0 ${-height}`} stroke={stem} strokeWidth={2} fill="none" />
      <ellipse cx={-5} cy={-height * 0.45} rx={5} ry={2.5} fill={stem} transform={`rotate(-30 -5 ${-height * 0.45})`} />
      {stage >= 2 && <ellipse cx={5} cy={-height * 0.65} rx={5} ry={2.5} fill={stem} transform={`rotate(30 5 ${-height * 0.65})`} />}
      {stage === 3 ? (
        <g transform={`translate(0 ${-height})`}>
          {[0, 72, 144, 216, 288].map((a) => (
            <ellipse key={a} cx={0} cy={-6} rx={3.5} ry={6} fill={`hsl(${hue} 70% 65%)`} transform={`rotate(${a})`} />
          ))}
          <circle r={3} fill="var(--accent)" />
        </g>
      ) : (
        <circle cx={0} cy={-height} r={stage === 2 ? 4 : 2.5} fill="var(--ok)" />
      )}
    </g>
  )
}

/** Jardín de postulaciones: cada postulación es una planta que crece con la etapa. */
export default function Garden({ apps, onSelect }: { apps: ApplicationItem[]; onSelect: (a: ApplicationItem) => void }) {
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
  const byId = new Map(apps.map((a) => [a.id, a]))
  const plants = plantLayout(apps, width, H - 40)
  return (
    <div ref={ref} className="relative overflow-hidden rounded-[var(--radius-card)] border border-line bg-surface"
         style={{ height: H }}>
      <div aria-hidden="true" className="absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-ok/15 to-transparent" />
      {plants.map((p) => {
        const app = byId.get(p.id)!
        return (
          <button
            key={p.id}
            type="button"
            onClick={() => onSelect(app)}
            aria-label={`${app.job.titulo} · ${app.estado}`}
            title={`${app.job.titulo} — ${app.job.empresa} (${app.estado})`}
            className="absolute -translate-x-1/2 -translate-y-full rounded-md p-1 hover:bg-bg/60"
            style={{ left: p.x, top: p.y + 40 }}
          >
            <svg width={30} height={52} viewBox="-15 -48 30 52" aria-hidden="true">
              <PlantShape stage={p.stage} hue={sealParams(app.job.empresa).hue} />
            </svg>
          </button>
        )
      })}
    </div>
  )
}
