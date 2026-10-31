// Sello de empresa: un patrón geométrico determinista derivado del nombre (sirve de avatar sin logo).

export function canonicalName(name: string): string {
  return name.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().trim().replace(/\s+/g, ' ')
}

/** Hash FNV-1a de 32 bits: rápido y estable, sin necesidad de criptografía en el navegador. */
export function fnv1a(text: string): number {
  let h = 0x811c9dc5
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i)
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h >>> 0
}

export interface SealParams {
  sides: number
  rotation: number
  rings: number
  hue: number
}

export function sealParams(company: string): SealParams {
  const h = fnv1a(canonicalName(company))
  return {
    sides: 3 + (h % 6),
    rotation: (h >>> 3) % 360,
    rings: 1 + ((h >>> 11) % 3),
    hue: (h >>> 16) % 360,
  }
}

export function polygonPoints(sides: number, radius: number, rotation: number, cx = 0, cy = 0): string {
  return Array.from({ length: sides }, (_, i) => {
    const a = (rotation * Math.PI) / 180 + (i * 2 * Math.PI) / sides
    return `${(cx + radius * Math.cos(a)).toFixed(2)},${(cy + radius * Math.sin(a)).toFixed(2)}`
  }).join(' ')
}
