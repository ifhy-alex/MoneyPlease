import { useEffect, useRef } from 'react'
import { createNoise2D } from 'simplex-noise'
import { prefersReducedMotion } from '../lib/motion'
import { mulberry32 } from './random'

const PARTICLES = 600
const FRAME_MS = 1000 / 30

/** Campo de flujo generativo: partículas que siguen ruido simplex. Se pausa con la pestaña oculta. */
export default function FlowField({ className = '' }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    const w = (canvas.width = canvas.clientWidth || 800)
    const h = (canvas.height = canvas.clientHeight || 600)
    const rnd = mulberry32(7)
    const noise = createNoise2D(rnd)
    const color = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#f2b84b'
    const pts = Array.from({ length: PARTICLES }, () => ({ x: rnd() * w, y: rnd() * h }))
    let z = 0
    let last = 0
    let frame = 0

    const draw = () => {
      ctx.fillStyle = color
      ctx.globalAlpha = 0.35
      for (const p of pts) {
        const angle = noise(p.x / 220, p.y / 220 + z) * Math.PI * 2
        p.x += Math.cos(angle) * 0.8
        p.y += Math.sin(angle) * 0.8
        if (p.x < 0 || p.x > w || p.y < 0 || p.y > h) {
          p.x = rnd() * w
          p.y = rnd() * h
        }
        ctx.fillRect(p.x, p.y, 1.2, 1.2)
      }
      ctx.globalAlpha = 1
    }

    if (prefersReducedMotion()) {
      for (let i = 0; i < 40; i++) draw()  // un solo cuadro estático
      return
    }
    const tick = (t: number) => {
      frame = requestAnimationFrame(tick)
      if (document.hidden || t - last < FRAME_MS) return
      last = t
      z += 0.0015
      ctx.globalAlpha = 0.06
      ctx.clearRect(0, 0, w, h)
      draw()
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [])
  return <canvas ref={ref} aria-hidden="true" className={`pointer-events-none ${className}`} />
}
