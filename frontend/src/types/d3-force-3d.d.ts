// Tipos mínimos de d3-force-3d (el paquete no trae los suyos): solo lo que usa el grafo 3D.
declare module 'd3-force-3d' {
  export interface Node3D {
    id?: string
    x?: number
    y?: number
    z?: number
    vx?: number
    vy?: number
    vz?: number
    [key: string]: unknown
  }
  export interface Force<N extends Node3D> {
    (alpha: number): void
    initialize?: (nodes: N[]) => void
  }
  export interface Simulation<N extends Node3D> {
    numDimensions(n: 1 | 2 | 3): Simulation<N>
    randomSource(source: () => number): Simulation<N>
    force(name: string, force: unknown): Simulation<N>
    stop(): Simulation<N>
    tick(iterations?: number): Simulation<N>
    nodes(): N[]
  }
  export function forceSimulation<N extends Node3D>(nodes?: N[], numDimensions?: 1 | 2 | 3): Simulation<N>
  export function forceLink<N extends Node3D>(links?: { source: string | N; target: string | N }[]): {
    id(fn: (n: N) => string): ReturnType<typeof forceLink<N>>
    distance(d: number): ReturnType<typeof forceLink<N>>
    strength(s: number): ReturnType<typeof forceLink<N>>
  }
  export function forceManyBody(): { strength(s: number): ReturnType<typeof forceManyBody> }
  export function forceCenter(x?: number, y?: number, z?: number): unknown
  export function forceCollide<N extends Node3D>(radius?: number | ((n: N) => number)): unknown
}
