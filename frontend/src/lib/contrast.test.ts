import { describe, expect, it } from 'vitest'
import { ratio } from './contrast'
import { TOKENS } from './tokens'

describe('contraste', () => {
  it('blanco sobre negro es 21:1', () => {
    expect(ratio('#000000', '#ffffff')).toBeCloseTo(21, 0)
  })

  it.each(['dark', 'light'] as const)('los tokens %s cumplen AA', (theme) => {
    const t = TOKENS[theme]
    for (const [fg, bg] of [[t.text, t.bg], [t.text, t.surface], [t.muted, t.bg], [t.muted, t.surface]]) {
      expect(ratio(fg, bg)).toBeGreaterThanOrEqual(4.5)
    }
  })
})
