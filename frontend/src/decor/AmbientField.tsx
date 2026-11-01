import { useEffect, useRef } from 'react'
import { createNoise3D } from 'simplex-noise'
import { seeded } from '../art/random'
import { prefersReducedMotion } from '../lib/motion'

const PARTICLES = 260
const FRAME_MS = 1000 / 30
const BG = '4, 6, 15'
const GLOW = '37, 71, 184'
const SILVER = '203, 213, 225'

/**
 * Fondo de toda la app: partículas azules muy tenues que siguen un campo de ruido simplex, con un halo
 * azul arriba. Va a 30 fps como máximo, se detiene con la pestaña oculta y queda quieto con movimiento reducido.
 */
export default function AmbientField() {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    const rnd = seeded('ambient')
    const noise = createNoise3D(rnd)
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    let w = 0
    let h = 0
    const resize = () => {
      w = window.innerWidth || 1280
      h = window.innerHeight || 800
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      paintBase()
    }
    const pts = Array.from({ length: PARTICLES }, (_, i) => ({ x: rnd(), y: rnd(), silver: i % 7 === 0 }))
    let z = 0

    function paintBase() {
      ctx!.fillStyle = `rgb(${BG})`
      ctx!.fillRect(0, 0, w, h)
    }
    const halo = () => {
      const g = ctx.createRadialGradient(w * 0.5, -h * 0.15, 0, w * 0.5, -h * 0.15, Math.max(w, h) * 0.75)
      g.addColorStop(0, `rgba(${GLOW}, 0.10)`)
      g.addColorStop(1, `rgba(${GLOW}, 0)`)
      ctx.fillStyle = g
      ctx.fillRect(0, 0, w, h)
    }
    const step = () => {
      ctx.fillStyle = `rgba(${BG}, 0.08)`  // estelas: cada cuadro borra un poco el anterior
      ctx.fillRect(0, 0, w, h)
      halo()
      for (const p of pts) {
        const angle = noise(p.x * 2.2, p.y * 2.2, z) * Math.PI * 2
        p.x += (Math.cos(angle) * 0.55) / w
        p.y += (Math.sin(angle) * 0.55) / h
        if (p.x < 0 || p.x > 1 || p.y < 0 || p.y > 1) {
          p.x = rnd()
          p.y = rnd()
        }
        ctx.fillStyle = p.silver ? `rgba(${SILVER}, 0.12)` : `rgba(${GLOW}, 0.18)`
        ctx.fillRect(p.x * w, p.y * h, 1.3, 1.3)
      }
    }

    resize()
    if (prefersReducedMotion()) {
      for (let i = 0; i < 60; i++) step()  // un solo cuadro con las estelas ya formadas
      return
    }

    let frame = 0
    let last = 0
    let running = false
    const tick = (t: number) => {
      if (document.hidden) {
        running = false  // no se programa el siguiente cuadro hasta que la pestaña vuelva
        return
      }
      frame = requestAnimationFrame(tick)
      if (t - last < FRAME_MS) return
      last = t
      z += 0.0012
      step()
    }
    const start = () => {
      if (running) return
      running = true
      frame = requestAnimationFrame(tick)
    }
    const onVisibility = () => { if (!document.hidden) start() }
    window.addEventListener('resize', resize)
    document.addEventListener('visibilitychange', onVisibility)
    start()
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('resize', resize)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [])
  return <canvas ref={ref} aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 h-full w-full" />
}
