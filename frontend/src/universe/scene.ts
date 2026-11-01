import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { mulberry32 } from '../art/random'
import { ease, flyTarget, isTap } from './camera'
import type { StarSpec, Vec3 } from './stars'

export class NoWebGL extends Error {
  constructor() {
    super('Tu navegador no puede mostrar el universo 3D')
  }
}

export interface Label {
  pos: Vec3
  text: string
  color: string
}

export interface SceneHandle {
  setStars(stars: StarSpec[]): void
  setLinks(pairs: [Vec3, Vec3][], opacity?: number): void
  setLabels(labels: Label[]): void
  setCenter(visible: boolean): void
  highlight(ids: string[] | null): void
  flyTo(pos: Vec3): void
  onHover(cb: (id: string | null, screen: { x: number; y: number }) => void): void
  onPick(cb: (id: string) => void): void
  dispose(): void
}

/** WebGL de verdad (jsdom y navegadores viejos no lo tienen). */
export function webglAvailable(): boolean {
  if (typeof window === 'undefined' || typeof (window as { WebGLRenderingContext?: unknown }).WebGLRenderingContext === 'undefined') {
    return false
  }
  try {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('webgl2') ?? canvas.getContext('webgl')
    return !!ctx && typeof (ctx as WebGLRenderingContext).getParameter === 'function'
  } catch {
    return false
  }
}

const FLY_MS = 1200
const BG = 0x04060f

/** Textura radial suave: el "brillo" de cada estrella. */
function glowTexture(): THREE.Texture {
  const c = document.createElement('canvas')
  c.width = c.height = 64
  const x = c.getContext('2d')!
  const g = x.createRadialGradient(32, 32, 0, 32, 32, 32)
  g.addColorStop(0, 'rgba(255,255,255,1)')
  g.addColorStop(0.22, 'rgba(255,255,255,0.75)')
  g.addColorStop(0.5, 'rgba(255,255,255,0.18)')
  g.addColorStop(1, 'rgba(255,255,255,0)')
  x.fillStyle = g
  x.fillRect(0, 0, 64, 64)
  return new THREE.CanvasTexture(c)
}

/** Anillo fino para las ofertas con publicaciones casi idénticas. */
function ringTexture(): THREE.Texture {
  const c = document.createElement('canvas')
  c.width = c.height = 64
  const x = c.getContext('2d')!
  x.strokeStyle = 'rgba(255,255,255,0.9)'
  x.lineWidth = 3
  x.beginPath()
  x.arc(32, 32, 26, 0, Math.PI * 2)
  x.stroke()
  return new THREE.CanvasTexture(c)
}

// Estrellas con tamaño, color y opacidad propios; mezcla aditiva para que brillen donde se juntan.
const VERTEX = `
  attribute float size;
  attribute float alpha;
  attribute vec3 tint;
  varying float vAlpha;
  varying vec3 vTint;
  uniform float scale;
  void main() {
    vAlpha = alpha;
    vTint = tint;
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = size * scale / -mv.z;
    gl_Position = projectionMatrix * mv;
  }`
const FRAGMENT = `
  uniform sampler2D map;
  varying float vAlpha;
  varying vec3 vTint;
  void main() {
    vec4 t = texture2D(map, gl_PointCoord);
    gl_FragColor = vec4(vTint * t.rgb, t.a * vAlpha);
  }`

function starMaterial(map: THREE.Texture, scale: number): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: { map: { value: map }, scale: { value: scale } },
    vertexShader: VERTEX, fragmentShader: FRAGMENT,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  })
}

function textSprite(text: string, color: string): THREE.Sprite {
  const c = document.createElement('canvas')
  const x = c.getContext('2d')!
  const font = '500 22px "Geist Mono Variable", ui-monospace, monospace'
  x.font = font
  // Margen holgado: la medida puede hacerse con la fuente de respaldo y el texto final ser algo más ancho.
  c.width = Math.ceil(x.measureText(text).width * 1.2) + 24
  c.height = 32
  x.font = font
  x.fillStyle = color
  x.textBaseline = 'middle'
  x.fillText(text, 8, 16)
  const tex = new THREE.CanvasTexture(c)
  tex.minFilter = THREE.LinearFilter
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }))
  sprite.scale.set(c.width / 64, c.height / 64, 1)
  return sprite
}

/**
 * Escena "Galaxia" del universo. Es la única pieza que toca three.js: la vista solo usa el `SceneHandle`.
 * Lanza `NoWebGL` si el navegador no puede crear un contexto WebGL.
 */
export function createScene(container: HTMLElement, opts: { reducedMotion: boolean }): SceneHandle {
  if (!webglAvailable()) throw new NoWebGL()
  let renderer: THREE.WebGLRenderer
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true })
  } catch {
    throw new NoWebGL()
  }
  const width = () => container.clientWidth || 800
  const height = () => container.clientHeight || 600
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.setSize(width(), height())
  renderer.setClearColor(BG)
  container.appendChild(renderer.domElement)
  renderer.domElement.style.touchAction = 'none'

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(55, width() / height(), 0.1, 300)
  camera.position.set(0, 5, 16)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.minDistance = 3
  controls.maxDistance = 40
  controls.autoRotate = !opts.reducedMotion
  controls.autoRotateSpeed = 0.6
  controls.addEventListener('start', () => { controls.autoRotate = false })

  const glow = glowTexture()
  const ring = ringTexture()
  const pxScale = () => height() * 0.9
  const disposables: { dispose(): void }[] = [glow, ring]

  // Fondo: estrellas lejanas, fijas.
  const rnd = mulberry32(9)
  const far = new THREE.BufferGeometry()
  far.setAttribute('position', new THREE.Float32BufferAttribute(Array.from({ length: 900 * 3 }, () => (rnd() - 0.5) * 160), 3))
  const farMat = new THREE.PointsMaterial({ color: 0x5e6e9c, size: 0.15, transparent: true, opacity: 0.6 })
  scene.add(new THREE.Points(far, farMat))
  disposables.push(far, farMat)

  // El perfil: una estrella grande en el centro.
  const center = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow, color: 0xffffff, blending: THREE.AdditiveBlending, depthWrite: false }))
  center.scale.set(2.6, 2.6, 2.6)
  scene.add(center)
  disposables.push(center.material)

  const starMat = starMaterial(glow, pxScale())
  const ringMat = starMaterial(ring, pxScale())
  disposables.push(starMat, ringMat)
  let stars: THREE.Points | null = null
  let rings: THREE.Points | null = null
  let specs: StarSpec[] = []
  let baseAlpha: number[] = []
  let links: THREE.LineSegments | null = null
  const labelGroup = new THREE.Group()
  scene.add(labelGroup)

  const pointsOf = (list: StarSpec[], sizeK: number, alphaOf: (s: StarSpec) => number) => {
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(list.flatMap((s) => s.pos), 3))
    geo.setAttribute('size', new THREE.Float32BufferAttribute(list.map((s) => s.size * sizeK), 1))
    geo.setAttribute('alpha', new THREE.Float32BufferAttribute(list.map(alphaOf), 1))
    geo.setAttribute('tint', new THREE.Float32BufferAttribute(list.flatMap((s) => new THREE.Color(s.color).toArray()), 3))
    return geo
  }

  let dirty = true
  const handle: SceneHandle = {
    setStars(list) {
      if (stars) { scene.remove(stars); stars.geometry.dispose() }
      if (rings) { scene.remove(rings); rings.geometry.dispose() }
      specs = list
      baseAlpha = list.map((s) => s.opacity)
      stars = new THREE.Points(pointsOf(list, 1, (s) => s.opacity), starMat)
      scene.add(stars)
      const ringed = list.filter((s) => s.ring)
      rings = new THREE.Points(pointsOf(ringed, 1.5, (s) => s.opacity * 0.55), ringMat)
      scene.add(rings)
      dirty = true
    },
    setLinks(pairs, opacity = 0.25) {
      if (links) { scene.remove(links); links.geometry.dispose(); (links.material as THREE.Material).dispose() }
      const geo = new THREE.BufferGeometry()
      geo.setAttribute('position', new THREE.Float32BufferAttribute(pairs.flatMap(([a, b]) => [...a, ...b]), 3))
      links = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ color: 0xcbd5e1, transparent: true, opacity }))
      scene.add(links)
      dirty = true
    },
    setLabels(labels) {
      for (const child of [...labelGroup.children]) {
        const s = child as THREE.Sprite
        s.material.map?.dispose()
        s.material.dispose()
        labelGroup.remove(s)
      }
      for (const l of labels) {
        const sprite = textSprite(l.text, l.color)
        sprite.position.set(l.pos[0], l.pos[1] + 0.9, l.pos[2])
        labelGroup.add(sprite)
      }
      dirty = true
    },
    setCenter(visible) {
      center.visible = visible
      dirty = true
    },
    highlight(ids) {
      if (!stars) return
      const keep = ids ? new Set(ids) : null
      const attr = stars.geometry.getAttribute('alpha') as THREE.BufferAttribute
      specs.forEach((s, i) => attr.setX(i, keep && !keep.has(s.id) ? baseAlpha[i] * 0.15 : baseAlpha[i]))
      attr.needsUpdate = true
      dirty = true
    },
    flyTo(pos) {
      controls.autoRotate = false
      const fromCam = camera.position.clone()
      const fromTarget = controls.target.clone()
      const toCam = new THREE.Vector3(...flyTarget(pos, [camera.position.x, camera.position.y, camera.position.z]))
      const toTarget = new THREE.Vector3(...pos)
      if (opts.reducedMotion) {
        camera.position.copy(toCam)
        controls.target.copy(toTarget)
        dirty = true
        return
      }
      flight = { start: performance.now(), fromCam, fromTarget, toCam, toTarget }
    },
    onHover(cb) { hoverCb = cb },
    onPick(cb) { pickCb = cb },
    dispose() {
      cancelAnimationFrame(frame)
      ro.disconnect()
      renderer.domElement.removeEventListener('pointerdown', onDown)
      renderer.domElement.removeEventListener('pointerup', onUp)
      renderer.domElement.removeEventListener('pointermove', onMove)
      handle.setLabels([])
      for (const obj of [stars, rings, links]) obj?.geometry.dispose()
      ;(links?.material as THREE.Material | undefined)?.dispose()
      for (const d of disposables) d.dispose()
      controls.dispose()
      renderer.dispose()
      renderer.domElement.remove()
    },
  }

  let flight: { start: number; fromCam: THREE.Vector3; fromTarget: THREE.Vector3; toCam: THREE.Vector3; toTarget: THREE.Vector3 } | null = null
  let hoverCb: (id: string | null, screen: { x: number; y: number }) => void = () => {}
  let pickCb: (id: string) => void = () => {}
  let hovered: string | null = null

  const raycaster = new THREE.Raycaster()
  const hit = (e: PointerEvent): StarSpec | null => {
    if (!stars) return null
    const rect = renderer.domElement.getBoundingClientRect()
    const ndc = new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1)
    raycaster.params.Points = { threshold: e.pointerType === 'touch' ? 0.5 : 0.25 }
    raycaster.setFromCamera(ndc, camera)
    const found = raycaster.intersectObject(stars).sort((a, b) => a.distanceToRay! - b.distanceToRay!)[0]
    return found?.index !== undefined ? specs[found.index] : null
  }
  const screenOf = (pos: Vec3) => {
    const v = new THREE.Vector3(...pos).project(camera)
    return { x: ((v.x + 1) / 2) * width(), y: ((1 - v.y) / 2) * height() }
  }
  const setHover = (s: StarSpec | null) => {
    hovered = s?.id ?? null
    hoverCb(hovered, s ? screenOf(s.pos) : { x: 0, y: 0 })
  }

  let down: { x: number; y: number; t: number } | null = null
  const onDown = (e: PointerEvent) => { down = { x: e.clientX, y: e.clientY, t: performance.now() } }
  const onMove = (e: PointerEvent) => { if (e.pointerType === 'mouse' && !e.buttons) setHover(hit(e)) }
  const onUp = (e: PointerEvent) => {
    if (!down || e.button !== 0) return
    const tap = isTap(e.clientX - down.x, e.clientY - down.y, performance.now() - down.t)
    down = null
    if (!tap) return  // fue un arrastre para rotar
    const s = hit(e)
    if (!s) { setHover(null); return }
    // Táctil: el primer toque muestra la estrella, el segundo sobre la misma la abre.
    if (e.pointerType !== 'mouse' && hovered !== s.id) setHover(s)
    else pickCb(s.id)
  }
  renderer.domElement.addEventListener('pointerdown', onDown)
  renderer.domElement.addEventListener('pointerup', onUp)
  renderer.domElement.addEventListener('pointermove', onMove)

  const ro = new ResizeObserver(() => {
    renderer.setSize(width(), height())
    camera.aspect = width() / height()
    camera.updateProjectionMatrix()
    starMat.uniforms.scale.value = ringMat.uniforms.scale.value = pxScale()
    dirty = true
  })
  ro.observe(container)

  let frame = 0
  const loop = (t: number) => {
    frame = requestAnimationFrame(loop)
    if (document.hidden) return
    if (flight) {
      const k = ease((t - flight.start) / FLY_MS)
      camera.position.lerpVectors(flight.fromCam, flight.toCam, k)
      controls.target.lerpVectors(flight.fromTarget, flight.toTarget, k)
      if (k >= 1) flight = null
      dirty = true
    }
    const moved = controls.update()
    if (moved || dirty) {
      renderer.render(scene, camera)
      dirty = false
    }
  }
  frame = requestAnimationFrame(loop)
  return handle
}
