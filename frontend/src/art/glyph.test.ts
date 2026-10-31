import { describe, expect, it } from 'vitest'
import { AREAS, normalizeAreas } from './glyph'

const zeros = { backend: 0, frontend: 0, datos: 0, cloud: 0, testing: 0, idiomas: 0 }

describe('huella del perfil', () => {
  it('normaliza contra el máximo de todas las versiones', () => {
    const out = normalizeAreas([{ areas: { ...zeros, backend: 4, cloud: 2 } }, { areas: { ...zeros, backend: 2 } }])
    expect(out[0][AREAS.indexOf('backend')]).toBe(1)
    expect(out[0][AREAS.indexOf('cloud')]).toBe(0.5)
    expect(out[1][AREAS.indexOf('backend')]).toBe(0.5)
  })

  it('todo en cero no produce NaN', () => {
    const [only] = normalizeAreas([{ areas: zeros }])
    expect(only).toEqual([0, 0, 0, 0, 0, 0])
  })

  it('sin versiones devuelve vacío', () => {
    expect(normalizeAreas([])).toEqual([])
  })
})
