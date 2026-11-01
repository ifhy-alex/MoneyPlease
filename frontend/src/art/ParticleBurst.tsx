import { useEffect, useRef } from 'react'
import { mulberry32 } from './random'

const DURATION = 1200
const PARTICLES = 60

/** Estallido breve de partículas (1,2 s) al pasar una postulación a Entrevista u Oferta. */
export default function ParticleBurst({ onDone, seed = Date.now() }: { onDone: () => void; seed?: number }) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    const w = (canvas.width = window.innerWidth)
    const h = (canvas.height = window.innerHeight)
    const rnd = mulberry32(seed)
    const parts = Array.from({ length: PARTICLES }, (_, i) => {
      const angle = (i / PARTICLES) * Math.PI * 2 + rnd() * 0.2
      const speed = 2 + rnd() * 5
      return { x: w / 2, y: h / 2, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed, silver: rnd() > 0.35 }
    })
    const start = performance.now()
    let frame = 0
    const tick = (t: number) => {
      const elapsed = t - start
      ctx.clearRect(0, 0, w, h)
      ctx.globalAlpha = Math.max(0, 1 - elapsed / DURATION)
      for (const p of parts) {
        p.x += p.vx
        p.y += p.vy
        p.vx *= 0.97
        p.vy *= 0.97
        ctx.fillStyle = p.silver ? '#CBD5E1' : '#2547B8'
        ctx.fillRect(p.x, p.y, 2, 2)
      }
      ctx.globalAlpha = 1
      if (elapsed < DURATION) frame = requestAnimationFrame(tick)
      else onDone()
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [onDone, seed])
  return <canvas ref={ref} data-testid="burst" aria-hidden="true" className="pointer-events-none fixed inset-0 z-40" />
}
