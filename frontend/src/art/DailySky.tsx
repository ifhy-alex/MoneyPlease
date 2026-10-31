import { useEffect, useRef } from 'react'
import { useDaily } from '../api/hooks'
import { skyParams } from './sky'

/** Encabezado de Inicio: el cielo de hoy, generado a partir de las ofertas nuevas y su score promedio. */
export default function DailySky() {
  const daily = useDaily()
  const ref = useRef<HTMLCanvasElement>(null)
  const today = daily.data?.at(-1)

  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx || !today) return
    const w = (canvas.width = canvas.clientWidth || 800)
    const h = (canvas.height = canvas.clientHeight || 120)
    const sky = skyParams(today.fecha, today.nuevas, today.score_promedio)
    const grad = ctx.createLinearGradient(0, 0, 0, h)
    grad.addColorStop(0, sky.top)
    grad.addColorStop(1, sky.bottom)
    ctx.fillStyle = grad
    ctx.fillRect(0, 0, w, h)
    ctx.fillStyle = '#fff6dd'
    for (const s of sky.stars) {
      ctx.globalAlpha = s.a
      ctx.beginPath()
      ctx.arc(s.x * w, s.y * h, s.r, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.globalAlpha = 1
  }, [today])

  if (!today) return null
  const label = `Cielo de hoy: ${today.nuevas} ofertas nuevas` +
    (today.score_promedio !== null ? `, score promedio ${today.score_promedio}` : '')
  return (
    <div className="relative overflow-hidden rounded-[var(--radius-card)]">
      <canvas ref={ref} role="img" aria-label={label} className="block h-28 w-full" />
      <p className="absolute bottom-2 left-4 text-sm text-[#e8e6f0] drop-shadow">{label}</p>
    </div>
  )
}
