import { useEffect, useMemo, useRef, useState } from 'react'
import { useSkillsGraph } from '../api/hooks'
import type { SkillsGraph } from '../api/types'
import { usePrefersReducedMotion } from '../lib/motion'
import { ArtFrame } from './ArtFrame'
import { layoutGraph, type GraphNode } from './skillGraphLayout'

/** Grafo de tus habilidades y las ofertas que las piden; las que piden y no tienes van punteadas. */
export default function SkillGraph({ onOpen }: { onOpen: (jobId: number) => void }) {
  const graph = useSkillsGraph()
  const narrow = window.matchMedia('(max-width: 639px)').matches
  const height = narrow ? 300 : 360
  const empty = !graph.data || graph.data.habilidades.length === 0
  return (
    <ArtFrame query={graph} height={height} empty={empty} emptyKind="sin-perfil"
              emptyTitle="El grafo aparece cuando haya ofertas evaluadas con tu perfil.">
      {graph.data && <GraphSvg data={graph.data} height={height} onOpen={onOpen} />}
    </ArtFrame>
  )
}

function GraphSvg({ data, height, onOpen }: { data: SkillsGraph; height: number; onOpen: (id: number) => void }) {
  const wrap = useRef<HTMLDivElement>(null)
  const reduced = usePrefersReducedMotion()
  const [width, setWidth] = useState(600)
  const [focus, setFocus] = useState<string | null>(null)
  const [shown, setShown] = useState(reduced)
  const { nodes, links } = useMemo(() => layoutGraph(data, width, height), [data, width, height])

  useEffect(() => {
    const el = wrap.current
    if (!el) return
    const measure = () => setWidth(el.clientWidth || 600)
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  useEffect(() => {
    if (reduced) return setShown(true)
    const t = requestAnimationFrame(() => setShown(true))
    return () => cancelAnimationFrame(t)
  }, [reduced])

  // Lo conectado al nodo resaltado (él mismo y sus vecinos) queda a opacidad completa.
  const near = useMemo(() => {
    if (!focus) return null
    const set = new Set([focus])
    for (const l of links) {
      if (l.source.id === focus) set.add(l.target.id)
      if (l.target.id === focus) set.add(l.source.id)
    }
    return set
  }, [focus, links])
  const opacity = (id: string) => (near && !near.has(id) ? 0.2 : 1)
  const highlight = (n: GraphNode) => ({
    onMouseEnter: () => setFocus(n.id), onMouseLeave: () => setFocus(null),
    onFocus: () => setFocus(n.id), onBlur: () => setFocus(null),
  })

  return (
    <div ref={wrap} className="glass overflow-hidden" style={{ height }}>
      <svg role="group" aria-label="Grafo de habilidades" data-animating={reduced ? 'false' : 'true'}
           viewBox={`0 0 ${width} ${height}`} width="100%" height={height}
           style={{ opacity: shown ? 1 : 0, transition: reduced ? 'none' : 'opacity 600ms ease-out' }}>
        {links.map((l) => (
          <line key={`${l.source.id}-${l.target.id}`} x1={l.source.x} y1={l.source.y} x2={l.target.x} y2={l.target.y}
                stroke={l.source.tiene === false ? 'var(--danger)' : 'var(--silver)'} strokeWidth={0.5}
                strokeOpacity={near && !(near.has(l.source.id) && near.has(l.target.id)) ? 0.06 : 0.35} />
        ))}
        {nodes.filter((n) => n.kind === 'offer').map((n) => (
          <rect key={n.id} role="button" tabIndex={0} aria-label={`Abrir ${n.label}`} {...highlight(n)}
                x={n.x - n.r} y={n.y - n.r} width={n.r * 2} height={n.r * 2} opacity={opacity(n.id)}
                fill={(n.puntaje ?? 0) >= 60 ? 'var(--text)' : 'var(--glow)'} className="cursor-pointer"
                onClick={() => onOpen(n.jobId!)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOpen(n.jobId!) } }} />
        ))}
        {nodes.filter((n) => n.kind === 'skill').map((n) => {
          const degree = data.habilidades.find((s) => `s:${s.nombre}` === n.id)?.grado ?? 0
          return (
            <g key={n.id} role="button" tabIndex={0} {...highlight(n)} opacity={opacity(n.id)}
               aria-label={`${n.label}: ${degree} ${degree === 1 ? 'oferta' : 'ofertas'}${n.tiene ? '' : ' (te falta)'}`}
               data-tiene={n.tiene ? 'true' : 'false'} className="cursor-default outline-none">
              <circle cx={n.x} cy={n.y} r={n.r} fill="var(--bg)"
                      stroke={n.tiene ? 'var(--silver)' : 'var(--danger)'} strokeWidth={1}
                      strokeDasharray={n.tiene ? undefined : '2 2'} />
              <text x={n.x + n.r + 4} y={n.y} dominantBaseline="central" fontSize={11}
                    fontFamily="var(--font-mono)" fill={n.tiene ? 'var(--silver)' : 'var(--muted)'}>{n.label}</text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
