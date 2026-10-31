import { useEffect, useRef } from 'react'
import { mulberry32 } from './random'

/** Lluvia breve de estrellas (1,5 s) al pasar una postulación a Entrevista u Oferta. */
export default function Starfall({ onDone, seed = Date.now() }: { onDone: () => void; seed?: number }) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    const w = (canvas.width = window.innerWidth)
    const h = (canvas.height = window.innerHeight)
    const rnd = mulberry32(seed)
    const stars = Array.from({ length: 40 }, () => ({
      x: rnd() * w, y: -rnd() * h * 0.3, vy: 3 + rnd() * 5, r: 1 + rnd() * 2.5,
    }))
    const color = getComputedStyle(document.documentElement).getPropertyValue('--accent') || '#f2b84b'
    const start = performance.now()
    let frame = 0
    const tick = (t: number) => {
      const elapsed = t - start
      ctx.clearRect(0, 0, w, h)
      ctx.globalAlpha = Math.max(0, 1 - elapsed / 1500)
      ctx.fillStyle = color
      for (const s of stars) {
        s.y += s.vy
        ctx.beginPath()
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
        ctx.fill()
      }
      if (elapsed < 1500) frame = requestAnimationFrame(tick)
      else onDone()
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [onDone, seed])
  return (
    <canvas ref={ref} data-testid="starfall" aria-hidden="true"
            className="pointer-events-none fixed inset-0 z-40" />
  )
}
