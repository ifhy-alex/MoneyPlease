import { describe, expect, it } from 'vitest'
import { createScene, NoWebGL, webglAvailable } from './scene'

describe('escena 3D', () => {
  it('sin WebGL lo detecta y no crea la escena', () => {
    expect(webglAvailable()).toBe(false)
    expect(() => createScene(document.createElement('div'), { reducedMotion: false })).toThrow(NoWebGL)
  })
})
