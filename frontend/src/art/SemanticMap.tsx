import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMap } from '../api/hooks'
import type { MapPoint } from '../api/types'
import { usePrefersReducedMotion } from '../lib/motion'
import { useIsNarrow } from '../lib/useIsNarrow'
import { ArtFrame } from './ArtFrame'
import { layoutMap, nearestPoint, topLinks, type ScreenPoint } from './mapLayout'

const ENTER_MS = 900
const FRAME_MS = 1000 / 30
const easeOutCubic = (t: number) => 1 - (1 - t) ** 3

/** Mapa semántico: el perfil en el centro y cada oferta a la distancia de su similitud real. */
export default function SemanticMap({ onOpen }: { onOpen: (jobId: number) => void }) {
  const map = useMap()
  const height = useIsNarrow() ? 300 : 420
  const puntos = map.data?.puntos ?? []
  return (
    <ArtFrame query={map} height={height} empty={puntos.length === 0}
              emptyTitle="El mapa se dibuja cuando haya ofertas analizadas."
              emptyText="Aparece después de la próxima ingesta con tu perfil guardado."
              noProfileTitle="Guarda tu perfil para ver el mapa de ofertas.">
      <MapCanvas puntos={puntos} height={height} onOpen={onOpen} />
    </ArtFrame>
  )
}

function MapCanvas({ puntos, height, onOpen }: { puntos: MapPoint[]; height: number; onOpen: (id: number) => void }) {
  const wrap = useRef<HTMLDivElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const reduced = usePrefersReducedMotion()
  const [width, setWidth] = useState(600)
  const [active, setActive] = useState<ScreenPoint | null>(null)
  const lastPointer = useRef('mouse')
  const points = useMemo(() => layoutMap(puntos, width, height), [puntos, width, height])
  const strong = puntos.filter((p) => (p.puntaje ?? 0) >= 60).length

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
    const c = canvas.current
    const ctx = c?.getContext('2d')
    if (!c || !ctx) return
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    c.width = width * dpr
    c.height = height * dpr
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    const cx = width / 2
    const cy = height / 2
    const links = topLinks(points)

    const draw = (enter: number, t: number) => {
      ctx.clearRect(0, 0, width, height)
      const drift = reduced ? 0 : 1.5
      const pos = (p: ScreenPoint): [number, number] => [
        cx + (p.px - cx) * enter + Math.sin(t / 1400 + p.job_id) * drift,
        cy + (p.py - cy) * enter + Math.cos(t / 1700 + p.job_id * 1.3) * drift,
      ]
      ctx.lineWidth = 0.6
      ctx.strokeStyle = 'rgba(203, 213, 225, 0.22)'
      for (const p of links) {
        const [x, y] = pos(p)
        ctx.beginPath()
        ctx.moveTo(cx, cy)
        ctx.lineTo(x, y)
        ctx.stroke()
      }
      for (const p of points) {
        const [x, y] = pos(p)
        ctx.fillStyle = p.tone === 'alto' ? '#F1F5F9' : p.tone === 'bajo' ? 'rgba(203, 213, 225, 0.6)' : 'rgba(37, 71, 184, 0.55)'
        ctx.beginPath()
        ctx.arc(x, y, p.r, 0, Math.PI * 2)
        ctx.fill()
        if (p.tone === 'alto') {
          ctx.strokeStyle = 'rgba(241, 245, 249, 0.25)'
          ctx.beginPath()
          ctx.arc(x, y, p.r + 4, 0, Math.PI * 2)
          ctx.stroke()
        }
      }
      ctx.fillStyle = '#F1F5F9'
      ctx.beginPath()
      ctx.arc(cx, cy, 4, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = 'rgba(241, 245, 249, 0.4)'
      for (const r of [10, 18]) {
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, Math.PI * 2)
        ctx.stroke()
      }
    }

    if (reduced) {
      draw(1, 0)
      return
    }
    let frame = 0
    let start = 0
    let last = 0
    const tick = (t: number) => {
      frame = requestAnimationFrame(tick)
      if (document.hidden || t - last < FRAME_MS) return
      last = t
      start ||= t
      draw(easeOutCubic(Math.min((t - start) / ENTER_MS, 1)), t)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [points, width, height, reduced])

  // Las coordenadas se calculan con el tamaño real del lienzo en el momento del evento.
  const hit = (clientX: number, clientY: number): ScreenPoint | null => {
    const rect = canvas.current!.getBoundingClientRect()
    const pts = layoutMap(puntos, rect.width || width, rect.height || height)
    return nearestPoint(pts, clientX - rect.left, clientY - rect.top)
  }

  return (
    <div ref={wrap} className="glass relative overflow-hidden" style={{ height }}>
      <Link to="/universo" className="glass panel mono absolute right-3 top-3 z-10 px-2.5 py-1 text-[11px] text-silver hover:border-silver">
        Explorar en 3D ↗
      </Link>
      <canvas
        ref={canvas}
        role="img"
        aria-label={`${puntos.length} ofertas; ${strong} con puntaje ≥ 60`}
        data-animating={reduced ? 'false' : 'true'}
        className="block w-full cursor-crosshair touch-manipulation"
        style={{ height }}
        onPointerMove={(e) => { if (e.pointerType === 'mouse') setActive(hit(e.clientX, e.clientY)) }}
        onPointerLeave={(e) => { if (e.pointerType === 'mouse') setActive(null) }}
        onPointerDown={(e) => { lastPointer.current = e.pointerType }}
        onClick={(e) => {
          // click solo llega con toques reales (no al deslizar) y después de los eventos de mouse simulados.
          if (e.button !== 0) return
          const p = hit(e.clientX, e.clientY)
          if (lastPointer.current === 'mouse') {
            if (p) onOpen(p.job_id)
            return
          }
          // Táctil: el primer toque muestra la oferta, el segundo sobre la misma la abre.
          if (p && active?.job_id === p.job_id) onOpen(p.job_id)
          else setActive(p)
        }}
      />
      {active && (
        <div role="tooltip"
             className="glass panel pointer-events-none absolute z-10 max-w-60 px-3 py-2 text-xs"
             style={{ left: Math.max(8, Math.min(active.px + 12, width - 248)), top: Math.max(active.py - 12, 8) }}>
          <p className="font-medium text-text">{active.titulo}</p>
          <p className="text-muted">{active.empresa}</p>
          <p className="mono mt-1 text-silver">{active.puntaje === null ? 'sin evaluar' : `${active.puntaje} / 100`}</p>
        </div>
      )}
    </div>
  )
}
