import { describe, expect, it } from 'vitest'
import { installGlassGlow } from './glow'

describe('brillo del vidrio', () => {
  it('pone --mx/--my relativos a la tarjeta bajo el puntero', () => {
    document.body.innerHTML = '<div class="glass-hover"><span id="hijo">x</span></div>'
    const card = document.querySelector<HTMLElement>('.glass-hover')!
    card.getBoundingClientRect = () => ({ left: 10, top: 20 } as DOMRect)
    const off = installGlassGlow()
    document.getElementById('hijo')!.dispatchEvent(new MouseEvent('pointermove', { bubbles: true, clientX: 40, clientY: 25 }))
    expect(card.style.getPropertyValue('--mx')).toBe('30px')
    expect(card.style.getPropertyValue('--my')).toBe('5px')
    off()
  })
})
