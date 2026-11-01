import { prefersReducedMotion } from './motion'

/** Mueve el brillo del borde de las tarjetas de vidrio (.glass-hover) hacia el puntero. */
export function installGlassGlow(root: Document = document): () => void {
  const onMove = (e: PointerEvent) => {
    if (prefersReducedMotion()) return  // con movimiento reducido el brillo queda fijo
    const el = (e.target as Element | null)?.closest?.('.glass-hover') as HTMLElement | null
    if (!el) return
    const box = el.getBoundingClientRect()
    el.style.setProperty('--mx', `${e.clientX - box.left}px`)
    el.style.setProperty('--my', `${e.clientY - box.top}px`)
  }
  root.addEventListener('pointermove', onMove, { passive: true })
  return () => root.removeEventListener('pointermove', onMove)
}
