import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll, vi } from 'vitest'
import { server } from './handlers'

// jsdom no trae matchMedia ni canvas: los simulamos. `reducedMotion` se puede cambiar por test.
export const media = { reducedMotion: false, dark: false, narrow: false }
const mediaListeners = new Set<() => void>()
/** Cambia una media query simulada y avisa a quien la escucha (por ejemplo, al girar el celular). */
export function setMedia(key: keyof typeof media, value: boolean) {
  media[key] = value
  for (const listener of mediaListeners) listener()
}
const matchesQuery = (query: string) =>
  query.includes('reduce') ? media.reducedMotion : query.includes('dark') ? media.dark
    : query.includes('max-width') ? media.narrow : false

beforeAll(() => {
  server.listen({ onUnhandledFrame: 'error' })
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      get matches() { return matchesQuery(query) },
      media: query,
      addEventListener: (_: string, fn: () => void) => { mediaListeners.add(fn) },
      removeEventListener: (_: string, fn: () => void) => { mediaListeners.delete(fn) },
      addListener: () => {},
      removeListener: () => {},
      onchange: null,
      dispatchEvent: () => false,
    }),
  })
  HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
    fillRect: vi.fn(), clearRect: vi.fn(), beginPath: vi.fn(), arc: vi.fn(), fill: vi.fn(), stroke: vi.fn(),
    moveTo: vi.fn(), lineTo: vi.fn(), createLinearGradient: () => ({ addColorStop: vi.fn() }),
    createRadialGradient: () => ({ addColorStop: vi.fn() }), save: vi.fn(), restore: vi.fn(),
    setTransform: vi.fn(), scale: vi.fn(), translate: vi.fn(), globalAlpha: 1, fillStyle: '', strokeStyle: '',
    lineWidth: 1,
  })) as unknown as typeof HTMLCanvasElement.prototype.getContext
  globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} } as unknown as typeof ResizeObserver
})

afterEach(() => {
  cleanup()
  server.resetHandlers()
  localStorage.clear()
  media.reducedMotion = false
  media.dark = false
  media.narrow = false
  mediaListeners.clear()
})

afterAll(() => server.close())
