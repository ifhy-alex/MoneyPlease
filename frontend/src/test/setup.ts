import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll, vi } from 'vitest'
import { server } from './handlers'

// jsdom no trae matchMedia ni canvas: los simulamos. `reducedMotion` se puede cambiar por test.
export const media = { reducedMotion: false, dark: false }

beforeAll(() => {
  server.listen({ onUnhandledFrame: 'error' })
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: query.includes('reduce') ? media.reducedMotion : query.includes('dark') ? media.dark : false,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
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
})

afterAll(() => server.close())
