/** Textura de grano sutil encima del fondo. */
export function Grain() {
  return (
    <svg aria-hidden="true" className="pointer-events-none fixed inset-0 z-0 h-full w-full opacity-[0.035]">
      <filter id="grain">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" />
      </filter>
      <rect width="100%" height="100%" filter="url(#grain)" />
    </svg>
  )
}
