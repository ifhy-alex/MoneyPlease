# Fase 5 — Universo 3D y duplicados Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar la vista `/universo` (galaxia 3D de ofertas y grafo 3D de habilidades, con búsqueda, filtros y nubes con nombre) y agrupar las publicaciones casi idénticas.

**Architecture:** El backend agrega funciones puras (`project3d`, `clusters`, `duplicate_groups`), el endpoint `/api/universe` y la agrupación de duplicados en top, explorar, detalle y feedback. En el frontend, three.js queda encerrado en `universe/scene.ts` detrás de `SceneHandle`; la lógica pura (estrellas, búsqueda, cámara, layout 3D) va en archivos aparte con sus pruebas. La vista se prueba con una escena falsa mediante `vi.mock`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, pgvector, numpy · React 19, TS, three@0.187.0, d3-force-3d@3.0.6, Vitest, MSW 3.

**Spec:** `docs/superpowers/specs/2026-11-01-fase5-universo-design.md`

## Global Constraints

- **Rama:** `fase5-universo`. Commits en español con prefijo convencional y **sin trailer `Co-Authored-By`**.
- **No leer** `backend/private/`, `backend/secrets/` ni `.env`.
- **Identidad y estilo:**
  - se usan los tokens de la Fase 4: `--bg #04060F`, `--silver #CBD5E1`, `--glow #2547B8`, `--text #F1F5F9`, `--danger #E0626F`;
  - textos de la interfaz en español;
  - con movimiento reducido no hay autorrotación ni vuelo animado (el vuelo es instantáneo).
- **Duplicados:** misma empresa (comparada con `canonical`) y similitud coseno **≥ 0.99**, es decir `cosine_distance <= 0.01`.
- **Carga:** three y d3-force-3d se cargan **solo** dentro de la vista `/universo` (lazy). `npm run build` no debe meterlos en el chunk de Inicio.
- **Comandos:** backend `cd backend && uv run pytest -q`; frontend `cd frontend && npx vitest run && npm run typecheck && npm run build`.

## Review Focus

1. **Universo sin ofertas o sin perfil:** muestra el mensaje o el `EmptyState`, no falla y el fondo sigue visible. Pruebas en la Tarea 4 (API) y la Tarea 9 (vista).
2. **Navegador sin WebGL:** muestra el mensaje con enlace a Inicio, sin excepción no capturada. Prueba en la Tarea 9.
3. **Un grupo de duplicados cuyo representante está en el top:** `/api/top?n=10` sigue devolviendo 10 ítems después de agrupar. Prueba en la Tarea 5.
4. **Quitar la marca (`null`) en una oferta con duplicados:** quita la etiqueta de todo el grupo. Prueba en la Tarea 5.
5. **Arrastrar en táctil:** no abre nada; solo un toque corto, de menos de 6 px y menos de 400 ms, cuenta como toque. Prueba de `isTap` en la Tarea 7.

---

### Task 1: Proyección 3D

**Files:** Modify `backend/moneyplease/projection.py` · Test `backend/tests/test_projection.py`

**Interfaces:**
- Produces: `project3d(profile: np.ndarray, jobs: np.ndarray, ids: list[int]) -> list[tuple[float, float, float, float]]`, que devuelve `(x, y, z, similitud)` en el orden de entrada.

- [ ] **Step 1: Tests**
  - `test_3d_radio_igual_que_2d`: con los `jobs_with([0.9, 0.7, 0.5, 0.3])` existentes, `‖(x,y,z)‖` vale `[0, 1/3, 2/3, 1]` con ±1e-6.
  - `test_3d_signo_determinista_sin_importar_el_orden`: igual que el test 2D, con 12 vectores aleatorios permutados.
  - `test_3d_menos_de_cuatro_en_espiral`: con 3 ofertas de similitud constante, cada `‖·‖` vale 0.5 y las tres direcciones son distintas (producto punto entre ellas < 0.99).
  - `test_3d_vacio`: devuelve `[]`.
- [ ] **Step 2:** `cd backend && uv run pytest tests/test_projection.py -q` → FAIL (ImportError).
- [ ] **Step 3: Implementar**
  - El radio se calcula igual que en `project`; conviene extraer `_radius(sims)` y compartirlo.
  - Con n ≥ 4, la dirección sale de las 3 componentes del SVD con el signo fijado; si la norma es menor que 1e-9, se usa `(1,0,0)`.
  - Con n < 4, se usa la espiral de Fibonacci con `i` = rango del id ordenado: `y = 1 − 2(i+0.5)/n`, `ρ = √(1−y²)`, `θ = i·π(3−√5)`.
- [ ] **Step 4:** el mismo comando → PASS.
- [ ] **Step 5:** `git commit -m "feat: proyección 3D de ofertas"`

### Task 2: Nubes con nombre

**Files:** Create `backend/moneyplease/clusters.py` · Modify `backend/moneyplease/skill_areas.py`, `backend/moneyplease/api/routes/graph.py` · Test `backend/tests/test_clusters.py`

**Interfaces:**
- Produces:
  - `clusters(coords: np.ndarray, k: int, seed: int = 0) -> list[int]`;
  - `cluster_count(n: int) -> int` (`n < 6` → 1; si no, `clamp(round(n/12), 2, 6)`);
  - `cluster_names(texts_by_cluster: list[list[str]]) -> list[str]`;
  - `display_skill(skill: str) -> str`, que se mueve de `graph._display` a `skill_areas`. `graph.py` la importa.

- [ ] **Step 1: Tests**
  - `test_clusters_determinista_e_indices_validos`: dos llamadas con la misma semilla dan el mismo resultado, y todos los índices están en `range(k)`.
  - `test_clusters_separa_grupos_obvios`: dos nubes de 10 puntos alrededor de (5,0,0) y (−5,0,0) quedan en 2 grupos sin mezclarse.
  - `test_cluster_count`: `cluster_count(5) == 1`, `cluster_count(30) == 2`, `cluster_count(60) == 5` y `cluster_count(300) == 6`.
  - `test_cluster_names`:
    - `[["Java y Spring Boot", "Java y Python"], ["Linux y redes"]]` da `["Java · Python", "Linux · Redes"]`. "spring boot" y "python" aparecen 1 vez cada uno y empatan, así que gana el orden alfabético: "python" va antes que "spring boot".
    - Una nube sin habilidades se llama `"Grupo 3"` si está en el índice 2.
- [ ] **Step 2:** `uv run pytest tests/test_clusters.py -q` → FAIL.
- [ ] **Step 3: Implementar** k-means++ con `default_rng(seed)`, como máximo 50 iteraciones y `k = min(k, n)`. Los nombres son las 2 habilidades más frecuentes (por cantidad de textos en que aparecen), unidas por `" · "`, pasadas por `display_skill`.
- [ ] **Step 4:** `uv run pytest tests/test_clusters.py tests/api/test_graph.py -q` → PASS.
- [ ] **Step 5:** `git commit -m "feat: nubes de ofertas con nombre"`

### Task 3: Detección de duplicados

**Files:** Create `backend/moneyplease/duplicates.py` · Test `backend/tests/test_duplicates.py`

**Interfaces:**
- Produces:
  - `duplicate_groups(items: list[tuple[int, str, list[float]]], score: dict[int, int], seen: dict[int, datetime]) -> dict[int, list[int]]`: devuelve representante → otros ids, solo para grupos de 2 o más.
  - `duplicates_of(session: Session, job: Job) -> list[Job]`: otras ofertas activas, de la misma empresa canónica y con `cosine_distance <= 0.01`. Si la oferta no tiene embedding, devuelve `[]`.

- [ ] **Step 1: Tests**
  - Misma empresa con similitud 0.995 se agrupa.
  - Empresas distintas con 0.999 no se agrupan.
  - Misma empresa con 0.98 no se agrupa.
  - Cadena: A~B y B~C (A y C a 0.985) forman un grupo de 3.
  - Representante: gana el mayor `score`; si empatan, el de `seen` más antiguo; si siguen empatados, el id menor.
  - `duplicates_of` (con `World` de `tests/api/conftest.py`): ofertas "HPE" y "hpe " casi iguales se encuentran entre sí; una oferta inactiva o sin embedding no aparece.
- [ ] **Step 2:** `uv run pytest tests/test_duplicates.py -q` → FAIL.
- [ ] **Step 3: Implementar**
  - Pares O(n²) con numpy (n ≤ 300) y union-find.
  - En `duplicates_of`, la empresa se compara en Python con `canonical`, después de un filtro SQL por `cosine_distance` con `enable_indexscan = off`.
- [ ] **Step 4:** el mismo comando → PASS.
- [ ] **Step 5:** `git commit -m "feat: detección de publicaciones casi idénticas"`

### Task 4: `GET /api/universe`

**Files:** Create `backend/moneyplease/api/routes/universe.py` · Modify `api/app.py`, `api/schemas.py`, `api/routes/map.py` (extraer la consulta común) · Test `backend/tests/api/test_universe.py`

**Interfaces:**
- Consumes: `project3d`, `clusters`, `cluster_count`, `cluster_names`, `duplicate_groups` y `skills_in`.
- Produces:
  - `map.py` expone `visible_jobs(session, active) -> list[tuple[Job, int | None, str | None, str | None]]`, que devuelve `(job, score, etiqueta, fit)` con exactamente los filtros actuales de `/api/map`. `get_map` la reutiliza.
  - Esquemas: `UniversePoint` (los campos de `MapPoint` + `z`, `fit: str | None`, `nube: int`, `duplicados: list[int]`), `Nube{id, nombre, x, y, z, n}` y `UniverseData{total, puntos, nubes}`.

- [ ] **Step 1: Tests**
  - 404 sin perfil.
  - `{"total":0,"puntos":[],"nubes":[]}` sin ofertas con embedding.
  - Los mismos ids que `/api/map` cuando no hay duplicados.
  - Dos ofertas "HPE" casi iguales (con `near(..., 0.999…)`): solo aparece una, con `duplicados == [la otra]`, y la que queda es la de mayor puntaje.
  - Cada `nube` en `range(len(nubes))`; el centroide de cada nube es el promedio de sus puntos (±1e-9); `sum(n) == total`.
- [ ] **Step 2:** `uv run pytest tests/api/test_universe.py -q` → FAIL (404 de la ruta).
- [ ] **Step 3: Implementar** con `visible_jobs`, luego `duplicate_groups` (ocultando los no representantes), luego `project3d` sobre los visibles, `clusters(coords, cluster_count(n))` y `cluster_names` sobre `titulo + descripcion`.
- [ ] **Step 4:** `uv run pytest tests/api -q` → PASS.
- [ ] **Step 5:** `git commit -m "feat(api): /api/universe con nubes y duplicados"`

### Task 5: Duplicados en top, explorar, detalle y feedback

**Files:** Modify `api/schemas.py`, `api/routes/top.py`, `api/routes/jobs.py` · Test `tests/api/test_top.py`, `tests/api/test_jobs.py`

**Interfaces:**
- Produces:
  - `DuplicateRef{job_id: int, url: str}`;
  - `TopItem.duplicados`, `ExploreItem.duplicados` y `JobDetail.duplicados`, todos `list[DuplicateRef]` con valor por defecto `[]`.

- [ ] **Step 1: Tests**
  - `test_top_agrupa_duplicados_y_mantiene_n`: con 12 ofertas evaluadas, de las cuales 2 son duplicados, `?n=10` devuelve 10 ítems; el del grupo trae 1 `duplicado` con su url, y la copia no aparece aparte.
  - `test_explorar_marca_sin_ocultar`: las dos copias aparecen y cada una lista a la otra.
  - `test_detalle_lista_duplicados`.
  - `test_feedback_aplica_al_grupo`: `no_interesa` sobre una copia deja `mala` en las dos; después, `null` sobre la otra no deja etiqueta en ninguna.
- [ ] **Step 2:** `uv run pytest tests/api -q -k "duplicad or grupo"` → FAIL.
- [ ] **Step 3: Implementar**
  - **top:** pide `limit(min(n, 50) + 10)` y recorre en orden de puntaje; si un ítem ya está entre los duplicados de un ítem anterior, lo salta. Corta en `n`.
  - **Duplicados por ítem:** `duplicates_of` en explorar, detalle y top.
  - **feedback:** aplica el upsert o el delete a `[job] + duplicates_of(job)` en una sola transacción.
- [ ] **Step 4:** `uv run pytest -q` → PASS (toda la suite).
- [ ] **Step 5:** `git commit -m "feat(api): agrupar publicaciones casi idénticas en top, explorar y feedback"`

### Task 6: Dependencias, tipos, hooks y aviso de duplicados en tarjetas

**Files:** Modify `frontend/package.json`, `src/api/types.ts`, `src/api/hooks.ts`, `src/test/handlers.ts`, `src/components/JobCard.tsx`, `src/components/JobDetail.tsx` · Create `src/types/d3-force-3d.d.ts` · Test `src/components/JobCard.test.tsx`

**Interfaces:**
- Produces:
  - **Tipos:** `DuplicateRef`, `UniversePoint`, `Nube` y `UniverseData`, con los mismos campos que la API. `TopItem`, `ExploreItem` y `JobDetail` ganan `duplicados: DuplicateRef[]`.
  - **Hook:** `useUniverse()`, con clave `['universe']` y `retry: false`. `useFeedback.onSettled` y `useSaveProfile` también invalidan `['universe']`.
  - **Mocks:** `handlers.ts` devuelve por defecto `GET /api/universe` como `{total:0,puntos:[],nubes:[]}`, más un helper `universePoint(id, puntaje, nube, extra?)`.
  - **`JobCard`:** recibe la prop `duplicados?: DuplicateRef[]`. Si no está vacía, muestra en mono el texto `+N publicación casi idéntica` (o `publicaciones casi idénticas` si N > 1) y los enlaces `↗ 2`, `↗ 3`…
  - **`JobDetail`:** lo mismo debajo del encabezado.

- [ ] **Step 1: Tests**
  - `JobCard.test.tsx`: con 1 duplicado aparece "+1 publicación casi idéntica" y un enlace a su url; sin duplicados no aparece nada.
  - Actualizar los fixtures `topItem` y `job` con `duplicados: []`.
- [ ] **Step 2:** `npx vitest run src/components` → FAIL.
- [ ] **Step 3: Implementar**
  - `npm i three@0.187.0 d3-force-3d@3.0.6` y `npm i -D @types/three@0.187.0`.
  - `d3-force-3d.d.ts` declara `forceSimulation`, `forceLink`, `forceManyBody`, `forceCenter` y `forceCollide`, con nodos `{x,y,z,vx,vy,vz}` y `numDimensions(3)`.
  - `Home` pasa `duplicados` a `JobCard`.
- [ ] **Step 4:** `npx vitest run && npm run typecheck` → PASS.
- [ ] **Step 5:** `git commit -m "feat(frontend): tipos del universo y aviso de publicaciones casi idénticas"`

### Task 7: Lógica pura del universo

**Files:** Create `src/universe/stars.ts`, `search.ts`, `camera.ts`, `graph3d.ts` · Test `src/universe/*.test.ts`

**Interfaces:**
- Produces:
  - **Tipos:**
    - `Vec3 = [number, number, number]`.
    - `StarSpec { id: string; pos: Vec3; size: number; color: string; opacity: number; ring: boolean; kind: 'offer' | 'skill' | 'missing'; label?: string }`.
    - `Filters { minScore: number; empresa: string | null; fit: 'todas' | 'practica' | 'junior' }`.
  - **`stars.ts`:**
    - `SCALE = 6`.
    - `offerStars(puntos: UniversePoint[], f: Filters): StarSpec[]`. El `id` es `"o:" + job_id`.
      - Puntaje ≥ 80: `#FFFFFF` y tamaño 1.1.
      - Puntaje 60–79: `#CBD5E1` y tamaño 0.7.
      - Puntaje < 60: `#CBD5E1`, tamaño 0.5 y opacidad 0.7.
      - Sin puntaje: `#2547B8` y tamaño 0.35.
      - Filtrada: opacidad 0.12.
      - `ring = duplicados.length > 0`.
    - `topLinks3d(puntos, n = 6): Vec3[]`.
  - **`search.ts`:** `search(q: string, items: { id: string; text: string }[]): { id: string; text: string }[]`. Ignora acentos y mayúsculas; los que empiezan por el texto van primero; como máximo 8; con `q` vacía devuelve `[]`.
  - **`camera.ts`:**
    - `flyTarget(target: Vec3, camera: Vec3, distance = 4): Vec3`: punto a `distance` del objetivo, sobre la recta cámara→objetivo.
    - `ease(t: number): number` (easeInOutCubic, limitado a [0,1]).
    - `isTap(dx: number, dy: number, ms: number): boolean`: `hypot < 6 && ms < 400`.
  - **`graph3d.ts`:** `layoutGraph3d(g: SkillsGraph, seed = 1): { nodes: { id: string; kind: 'skill' | 'offer'; label: string; pos: Vec3; tiene?: boolean; puntaje?: number; jobId?: number; grado?: number }[]; links: [string, string][]; isolated: string[] }`. Solo habilidades con grado > 0, igual que en 2D; d3-force-3d con `numDimensions(3)`, `randomSource(mulberry32(seed))` y 300 ticks.

- [ ] **Step 1: Tests**
  - **stars:** tamaños y colores en 85, 70, 40 y null; las filtradas por empresa, puntaje mínimo y tipo bajan a 0.12; la posición es `[x*6, y*6, z*6]`; `ring` es verdadero si hay duplicados.
  - **search:** "hpe" encuentra "HPE"; "energia" encuentra "Energía"; con 12 coincidencias devuelve 8; el que empieza por el texto va antes que el que lo contiene.
  - **camera:**
    - `flyTarget([0,0,0], [0,0,10])` da `[0,0,4]`;
    - `ease(0) = 0`, `ease(1) = 1` y `ease(0.5) = 0.5`;
    - `isTap(2, 3, 120)` es verdadero, `isTap(10, 0, 100)` es falso e `isTap(1, 1, 600)` es falso.
  - **graph3d:** la misma semilla da las mismas posiciones; todos los nodos quedan a menos de 60 unidades del origen; `isolated` es `['Python']` con `skillsGraph()`.
- [ ] **Step 2:** `npx vitest run src/universe` → FAIL.
- [ ] **Step 3: Implementar** según el bloque Interfaces.
- [ ] **Step 4:** el mismo comando → PASS, y `npm run typecheck` → OK.
- [ ] **Step 5:** `git commit -m "feat(frontend): lógica del universo (estrellas, búsqueda, cámara, grafo 3D)"`

### Task 8: Escena three.js

**Files:** Create `src/universe/scene.ts` · Test `src/universe/scene.test.ts`

**Interfaces:**
- Produces:
  - `webglAvailable(): boolean`.
  - `class NoWebGL extends Error`.
  - `createScene(container: HTMLElement, opts: { reducedMotion: boolean }): SceneHandle`. Lanza `NoWebGL` si no hay WebGL.
  - `SceneHandle`:
    - `setStars(stars: StarSpec[])`, `setLinks(pairs: [Vec3, Vec3][])`, `setLabels(labels: { pos: Vec3; text: string; color: string }[])`;
    - `highlight(ids: string[] | null)`;
    - `flyTo(pos: Vec3)`;
    - `onHover(cb: (id: string | null, screen: { x: number; y: number }) => void)`;
    - `onPick(cb: (id: string) => void)`;
    - `dispose()`.

- [ ] **Step 1: Tests** (jsdom no tiene WebGL): con `getContext` que devuelve `null`, `webglAvailable()` es falso y `createScene` lanza `NoWebGL`.
- [ ] **Step 2:** `npx vitest run src/universe/scene.test.ts` → FAIL.
- [ ] **Step 3: Implementar** según la spec §2.3:
  - fondo de 900 estrellas;
  - estrellas como `Points` con un `ShaderMaterial` mínimo (tamaño, color y opacidad por vértice, textura radial, `AdditiveBlending`);
  - anillos como `Points` aparte con textura de anillo; sprite del perfil; `LineSegments`;
  - etiquetas como `Sprite` con `CanvasTexture`;
  - `OrbitControls` de `three/examples/jsm/controls/OrbitControls.js`, con amortiguación, distancia 3–40 y autorrotación 0.6 (desactivada con movimiento reducido; se detiene en `start`);
  - `Raycaster` con umbral de puntos 0.25, o 0.5 si `pointerType === 'touch'`;
  - el toque se decide con `isTap`: en táctil, el primero hace hover y el segundo sobre la misma estrella hace pick;
  - render bajo demanda más bucle mientras hay amortiguación, vuelo o autorrotación; se pausa con `document.hidden`;
  - `ResizeObserver`; `dispose` libera todo.
- [ ] **Step 4:** `npx vitest run src/universe && npm run typecheck` → PASS.
- [ ] **Step 5:** `git commit -m "feat(frontend): escena three.js del universo"`

### Task 9: Vista `/universo`, pestaña Ofertas

**Files:** Create `src/views/Universe.tsx`, `src/universe/Panel.tsx` · Modify `src/App.tsx` · Test `src/views/Universe.test.tsx`

**Interfaces:**
- Consumes: `useUniverse`, `createScene` / `NoWebGL`, `offerStars`, `topLinks3d`, `search`, `JobDetail` y `ArtFrame`, que se reusa para el 404 sin perfil con `noProfileTitle`.
- Produces: la ruta `<Route path="/universo" element={<Universe />} />` (lazy). La pestaña se lee de `?vista=ofertas|habilidades`; la que se usa por defecto es ofertas.

- [ ] **Step 1: Tests**

Se hace `vi.mock('../universe/scene', …)` con una escena falsa que guarda las llamadas y expone `__pick(id)` y `__hover(id)`.
- Con 3 puntos, `setStars` recibe 3 estrellas y `setLabels` recibe los nombres de las nubes.
- Escribir "Oferta 2" y Enter llama a `flyTo` con `[x*6, y*6, z*6]` del punto 2.
- El filtro "Puntaje mínimo" en 80 hace que la última llamada a `setStars` tenga la opacidad de las demás en 0.12.
- `__pick('o:1')` abre el diálogo "Detalle de la oferta".
- Hacer clic en una nube del panel llama a `flyTo` con su centroide ×6.
- Si `createScene` lanza `NoWebGL`, aparece "Tu navegador no puede mostrar el universo 3D" con un enlace a "/".
- Con `media.reducedMotion = true`, `createScene` se llama con `{ reducedMotion: true }`.
- Al desmontar se llama a `dispose`.
- `/api/universe` con 404 muestra "Guarda tu perfil" y un enlace a Perfil.
- Con 0 puntos aparece "Todavía no hay ofertas para mostrar en el universo."
- [ ] **Step 2:** `npx vitest run src/views/Universe.test.tsx` → FAIL.
- [ ] **Step 3: Implementar**
  - Layout de pantalla completa: canvas detrás y panel `.glass panel` a la izquierda (280 px en escritorio; en el celular, plegable abajo).
  - El tooltip flota en las coordenadas de pantalla de `onHover`.
  - Botón "← Volver" que lleva a `/`.
  - Pestañas "Ofertas | Habilidades" (`role="tablist"`).
- [ ] **Step 4:** `npx vitest run && npm run typecheck && npm run build` → PASS. El chunk de `Universe` contiene three y el `index` no.
- [ ] **Step 5:** `git commit -m "feat(frontend): vista /universo con galaxia de ofertas, búsqueda y filtros"`

### Task 10: Pestaña Habilidades

**Files:** Modify `src/views/Universe.tsx`, `src/universe/Panel.tsx` · Test `src/views/Universe.test.tsx`

**Interfaces:**
- Consumes: `useSkillsGraph` y `layoutGraph3d`.
- Produces, en `stars.ts`: `skillStars(layout): StarSpec[]`.
  - Habilidad que tienes: `#CBD5E1`, tamaño `0.8 + 0.8·grado/max` y `label`.
  - Habilidad que falta: `#E0626F`, opacidad 0.8 y `kind` `'missing'`.
  - Oferta: tamaño 0.35, `#FFFFFF` si el puntaje es ≥ 60 y `#2547B8` si no.

- [ ] **Step 1: Tests**
  - `?vista=habilidades`: `setLabels` incluye "Java" y "Docker"; `setLinks` recibe 3 pares.
  - `__hover('s:Docker')` llama a `highlight` con `['s:Docker', 'o:1']`.
  - `__pick('s:Java')` lista en el panel "Oferta 1" y "Oferta 2" ordenadas por puntaje.
  - `__pick('o:2')` abre el detalle.
  - Los chips "Sin ofertas que las pidan todavía: Python" aparecen.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4:** `npx vitest run && npm run typecheck` → PASS.
- [ ] **Step 5:** `git commit -m "feat(frontend): grafo de habilidades en 3D"`

### Task 11: Enlaces desde Inicio y Perfil, y README

**Files:** Modify `src/art/SemanticMap.tsx`, `src/views/Profile.tsx`, `README.md` · Test `src/views/Home.test.tsx`, `src/views/Profile.test.tsx`

- [ ] **Step 1: Tests**
  - Inicio con puntos en el mapa tiene un enlace "Explorar en 3D" con `href` `/universo`.
  - Perfil con grafo tiene un enlace "Ver en 3D" con `href` `/universo?vista=habilidades`.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3: Implementar.** El enlace del mapa va en la esquina superior derecha del recuadro, `.glass panel` mono de 11 px. En el README, el apartado "Universo 3D".
- [ ] **Step 4:** suites completas de backend y frontend, typecheck y build → PASS.
- [ ] **Step 5:** `git commit -m "feat(frontend): enlaces al universo 3D desde Inicio y Perfil"`

### Task 12: Verificación en navegador

- [ ] `docker compose up -d --build web`; luego `curl localhost:8000/api/universe` muestra un `total` mayor que 0.
- [ ] Antes de las capturas, comprobar que el panel del navegador está **visible** (`tabs_context`). Si está oculto, pedirle al usuario que lo muestre con Ctrl+Shift+B.
- [ ] En escritorio:
  - en `/universo`, la autorrotación funciona;
  - arrastrar rota y la rueda hace zoom;
  - buscar "HPE" hace volar la cámara;
  - el tooltip y el detalle funcionan;
  - las ofertas duplicadas de HPE tienen anillo y en el top aparecen como una sola tarjeta;
  - la pestaña Habilidades funciona;
  - la consola no tiene errores.
- [ ] A 375 px: no hay scroll horizontal, el panel se pliega y los toques funcionan.
- [ ] Los hallazgos se corrigen con su prueba primero y en commits propios.
