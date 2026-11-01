import { describe, expect, it } from 'vitest'

// El rediseño retiró las metáforas de naturaleza: que no vuelvan por accidente en código ni textos.
const files = import.meta.glob('/src/**/*.{ts,tsx}', { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const NATURE = /\b(garden|jard[ií]n|starfall|constellation|constelaci[oó]n|DailySky|NightGradient)\b/i

describe('sin metáforas de naturaleza', () => {
  it('ningún archivo las menciona', () => {
    const offenders = Object.entries(files)
      .filter(([path]) => !path.endsWith('naming.test.ts'))
      .filter(([, text]) => NATURE.test(text))
      .map(([path]) => path)
    expect(offenders).toEqual([])
  })
})
