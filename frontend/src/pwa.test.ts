import { describe, expect, it } from 'vitest'
import html from '../index.html?raw'
import manifest from '../public/manifest.json'

const pngs = Object.keys(import.meta.glob('../public/*.png')).map((p) => p.replace('../public', ''))

describe('app instalable', () => {
  it('el manifest abre la app a pantalla completa con los colores del tema', () => {
    expect(manifest).toMatchObject({ name: 'MoneyPlease', start_url: '/', display: 'standalone',
                                     background_color: '#04060F', theme_color: '#04060F' })
  })

  it('trae íconos de 192 y 512, uno maskable, y todos existen', () => {
    expect(manifest.icons.map((i) => i.sizes)).toEqual(expect.arrayContaining(['192x192', '512x512']))
    expect(manifest.icons.some((i) => i.purpose === 'maskable')).toBe(true)
    for (const i of manifest.icons) expect(pngs).toContain(i.src)
    expect(pngs).toContain('/apple-touch-icon.png')
  })

  it('index.html enlaza el manifest y el ícono de iOS', () => {
    expect(html).toContain('<link rel="manifest" href="/manifest.json"')
    expect(html).toContain('<link rel="apple-touch-icon" href="/apple-touch-icon.png"')
    expect(html).toContain('name="apple-mobile-web-app-capable" content="yes"')
  })
})
