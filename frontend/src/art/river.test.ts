import { describe, expect, it } from 'vitest'
import { toSeries } from './river'

describe('flujo de ofertas', () => {
  it('rellena con 0 las combinaciones que faltan', () => {
    const s = toSeries([
      { semana: '2026-10-19', fuente: 'workday', nuevas: 5 },
      { semana: '2026-10-26', fuente: 'greenhouse', nuevas: 2 },
    ])
    expect(s.semanas).toEqual(['2026-10-19', '2026-10-26'])
    expect(s.fuentes).toEqual(['greenhouse', 'workday'])
    expect(s.matrix).toEqual([[0, 5], [2, 0]])
  })

  it('sin datos devuelve todo vacío', () => {
    expect(toSeries([])).toEqual({ semanas: [], fuentes: [], matrix: [] })
  })
})

describe('flujo de ofertas con historia corta', () => {
  it('recorta las semanas vacías del principio', () => {
    const s = toSeries([
      { semana: '2026-10-12', fuente: 'workday', nuevas: 0 },
      { semana: '2026-10-19', fuente: 'workday', nuevas: 0 },
      { semana: '2026-10-26', fuente: 'workday', nuevas: 9 },
    ])
    expect(s.semanas).toEqual(['2026-10-26'])
    expect(s.matrix).toEqual([[9]])
  })
})

describe('colores del flujo', () => {
  it('usa la paleta medianoche y plata', async () => {
    const { SOURCE_COLORS } = await import('./river')
    expect(SOURCE_COLORS).toHaveLength(6)
    expect(SOURCE_COLORS).not.toContain('var(--accent)')
    expect(SOURCE_COLORS[0]).toBe('var(--silver)')
  })
})
