/** Centro en pantalla de la postulación (tarjeta del tablero o nodo del pipeline), si está a la vista. */
export function burstOrigin(appId: number): { x: number; y: number } | null {
  const el = document.querySelector<HTMLElement>(`[data-app-id="${appId}"]`)
  if (!el) return null
  const r = el.getBoundingClientRect()
  return { x: r.left + r.width / 2, y: r.top + r.height / 2 }
}
