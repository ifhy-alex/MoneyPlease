import { describe, expect, it } from 'vitest'
import { toSeries } from './river'

describe('río de ofertas', () => {
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

describe('río de ofertas con historia corta', () => {
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
