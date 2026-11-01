import { describe, expect, it } from 'vitest'
import { ratio } from './contrast'
import { TOKENS } from './tokens'

describe('contraste', () => {
  it('blanco sobre negro es 21:1', () => {
    expect(ratio('#000000', '#ffffff')).toBeCloseTo(21, 0)
  })

  it('los tokens de medianoche y plata cumplen AA', () => {
    const t = TOKENS
    const pairs = [[t.text, t.bg], [t.text, t.glass], [t.muted, t.bg], [t.muted, t.glass], [t.silver, t.bg], [t.silver, t.glass]]
    for (const [fg, bg] of pairs) expect(ratio(fg, bg)).toBeGreaterThanOrEqual(4.5)
  })
})
