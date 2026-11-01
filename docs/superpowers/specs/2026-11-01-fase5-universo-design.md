# Fase 5: Universo 3D y agrupación de duplicados

**Fecha:** 2026-11-01 · **Rama:** `fase5-universo`

## Por qué

El usuario quiere **explorar** sus ofertas y habilidades en 3D, como un mapa de estrellas:
- entrar a una vista propia;
- rotar, acercarse y alejarse;
- descubrir grupos;
- buscar y filtrar.

Además, el top muestra publicaciones repetidas. Por ejemplo, HPE "Intern - Bachelor's Tech" y "Intern - Bachelors Tech" tienen requisiciones distintas (1216552 y 1214221), se publicaron un día aparte y sus descripciones tienen una similitud de 0.997.

**Listo cuando:**
- `/universo` muestra las ofertas como galaxia 3D navegable, con grupos con nombre, buscador con vuelo de cámara y filtros.
- La pestaña Habilidades muestra el grafo en 3D.
- Inicio y Perfil enlazan a esa vista.
- Las publicaciones casi idénticas se agrupan en el top y en el universo.
- Las suites de backend y frontend pasan y el build compila.
- La verificación en navegador, con el panel **visible**, muestra las animaciones completas en escritorio y celular.

## Decisiones del usuario

| Tema | Decisión |
|---|---|
| Alcance | Explorar y contemplar, en una sola fase |
| Dónde vive | Página propia `/universo`; el 2D de Inicio y Perfil se queda como vista previa con botón |
| Estilo | "Galaxia": estrellas con brillo aditivo, tú al centro, fondo de estrellas lejanas |
| Duplicados | Misma empresa y similitud ≥ 0.99: se agrupan al mostrar; el feedback se aplica al grupo |

## 1. Backend

### 1.1 Proyección 3D (`moneyplease/projection.py`)

`project3d(profile, jobs, ids) -> list[tuple[x, y, z, similitud]]`

- **Radio:** el mismo que en 2D, `r = (s_max − s)/(s_max − s_min)`, o 0.5 si la similitud es constante.
- **Dirección:** PCA de los residuos `v − s·p` centrados, con las primeras 3 componentes y el signo fijado como en 2D (la carga de mayor valor absoluto, positiva).
  - `d = (c1, c2, c3) / ‖(c1, c2, c3)‖`.
  - Si `‖·‖ < 1e-9`, se usa `d = (1, 0, 0)`.
- **Pocas ofertas:** con menos de 4, las direcciones salen de una espiral de Fibonacci sobre la esfera, ordenadas por id.
- **Resultado:** `(x, y, z) = r·d`.

### 1.2 Nubes (`moneyplease/clusters.py`)

`clusters(coords: np.ndarray, k: int, seed: int = 0) -> list[int]`: k-means sobre las coordenadas 3D.
- La inicialización es k-means++ con `numpy.random.default_rng(seed)`.
- Hace como máximo 50 iteraciones.
- Es determinista.

`k = clamp(round(n / 12), 2, 6)`; si `n < 6`, se usa `k = 1`.

`cluster_names(texts_por_nube) -> list[str]`:
- toma las 2 habilidades más frecuentes de la nube con `skills_in`, en el formato de `_display` de `graph.py`, unidas por `" · "`;
- desempata por nombre;
- si la nube no tiene ninguna habilidad, la nombra "Grupo {i+1}".

### 1.3 Duplicados (`moneyplease/duplicates.py`)

`duplicate_groups(jobs: list[tuple[id, empresa, embedding]]) -> dict[int, list[int]]`
- Une con union-find los pares de **la misma empresa** (comparada con `canonical`) cuya similitud coseno es **≥ 0.99**.
- Devuelve `representante → [otros ids]`.
- **Representante:** el de mayor puntaje con el perfil activo; si empatan, el de `primera_vez_visto` más antigua; si siguen empatados, el id menor.

`duplicates_of(session, job_id) -> list[int]`: las ofertas activas que forman grupo con esa oferta. Se calcula en SQL con `cosine_distance <= 0.01` y la misma empresa.

### 1.4 `GET /api/universe`

Respuesta:
```json
{ "total": 120,
  "puntos": [ { "job_id": 1, "titulo": "…", "empresa": "…", "x": 0.1, "y": -0.4, "z": 0.3, "similitud": 0.83,
                "puntaje": 95, "fit": "practica", "etiqueta": null, "nube": 2, "duplicados": [8827] } ],
  "nubes": [ { "id": 2, "nombre": "Python · Java", "x": 0.2, "y": -0.3, "z": 0.4, "n": 14 } ] }
```

- **Qué ofertas entran:** las mismas que `/api/map`: activas, con embedding, filtro de lugar en SQL, `enable_indexscan = off`, sin `no_interesa`, que pasan `passes` y como máximo 300.
- **Duplicados:** se agrupan y solo queda el representante, con `duplicados` (los ids ocultos).
- **Nubes:** la posición de cada nube es el centroide de sus puntos.
- **Errores:** sin perfil, 404 "Todavía no hay perfil guardado".

### 1.5 Duplicados en el resto de la API

- **`/api/top`:** quita los no representantes y agrega a cada ítem `duplicados: [{ job_id, url }]`. Pide `n + 10` filas para seguir devolviendo `n` después de agrupar.
- **`/api/jobs` (Explorar):** no oculta nada, porque la lista es completa y paginada. Agrega a cada ítem `duplicados: [{ job_id, url }]`.
- **`POST /api/jobs/{id}/feedback`:** aplica la misma etiqueta, o la quita si es `null`, a `job_id` y a `duplicates_of(job_id)` en la misma transacción.

## 2. Frontend

### 2.1 Dependencias
- `three@0.187.0` y `@types/three@0.187.0`.
- `d3-force-3d@3.0.6`, con una declaración de tipos local en `src/types/d3-force-3d.d.ts`.
- Todo se carga solo en `/universo`, con `React.lazy` sobre la vista, así que el bundle de Inicio no crece.

### 2.2 Estructura (`src/universe/`)

| Archivo | Responsabilidad |
|---|---|
| `scene.ts` | Única pieza que toca three.js. Expone `createScene(container, { reducedMotion }) → SceneHandle` |
| `stars.ts` | Pura: de puntos y filtros a especificación de estrellas (posición ×6 unidades, tamaño, color, opacidad) |
| `search.ts` | Pura: búsqueda sin acentos ni mayúsculas en título, empresa y nombres de habilidades; hasta 8 resultados, los que empiezan por el texto primero |
| `camera.ts` | Pura: `flyTarget(pos)` (cámara a 4 unidades del objetivo, misma dirección de vista) y `ease(t)` (easeInOutCubic) |
| `graph3d.ts` | Pura: layout d3-force-3d con semilla fija (`randomSource(mulberry32(seed))`) y 300 ticks |
| `Panel.tsx` | Buscador, filtros, lista de nubes o habilidades, plegable |
| `views/Universe.tsx` | Ruta `/universo?vista=ofertas|habilidades`: arma la escena, el panel y `JobDetail` |

**`SceneHandle`:**
- `setStars(stars)`, `setLinks(pairs)`, `setLabels(labels)`;
- `highlight(ids | null)`;
- `flyTo(pos)`: dura 1.2 s, o es instantáneo con movimiento reducido;
- `onHover(cb)`, `onPick(cb)`;
- `dispose()`.

En las pruebas, `scene.ts` se reemplaza con `vi.mock` por una escena falsa que registra las llamadas.

### 2.3 Aspecto "Galaxia" (`scene.ts`)
- **Fondo:** `#04060F` y 900 estrellas lejanas `#5E6E9C`, de tamaño 0.15 y opacidad 0.6.
- **Estrellas:** `Points` con textura radial generada en canvas, `AdditiveBlending` y `depthWrite = false`.
  - Puntaje ≥ 80: blanco y tamaño 1.1.
  - Puntaje 60–79: plata `#CBD5E1` y tamaño 0.7.
  - Puntaje < 60: plata al 70 % y tamaño 0.5.
  - Sin evaluar: `#2547B8` y tamaño 0.35.
  - Filtradas: opacidad 0.12.
- **Duplicados:** un anillo (sprite de anillo) alrededor de la estrella.
- **Perfil:** sprite blanco de tamaño 2.6 en el origen.
- **Líneas de luz:** del centro a las 6 mejores ofertas, en `#CBD5E1` al 25 %.
- **Etiquetas** (nombres de nubes o de habilidades): sprites de texto (canvas → textura) en Geist Mono de 11 px plata, que siempre miran a la cámara.
- **Controles:** `OrbitControls` con amortiguación, distancia de 3 a 40 y autorrotación de 0.6 que se detiene al primer gesto. Con movimiento reducido no hay autorrotación.
- **Selección:** con `Raycaster`, con umbral de puntos de 0.25 en escritorio y 0.5 en táctil.
  - Mouse: hover muestra el tooltip y clic abre.
  - Táctil: el primer toque muestra el tooltip y el segundo sobre la misma estrella abre.
  - Arrastrar no abre nada.
- **Rendimiento:** DPR limitado a 2 y render solo cuando cambia algo o hay animación (amortiguación, vuelo o autorrotación). Se pausa con la pestaña oculta. `dispose()` libera geometrías, materiales, texturas y el renderer.
- **Sin WebGL:** si `WebGLRenderingContext` no existe o falla la creación del contexto, se muestra "Tu navegador no puede mostrar el universo 3D" con un enlace a Inicio.

### 2.4 Pestaña Ofertas
- **Datos:** `GET /api/universe`.
- **Panel:**
  - buscador: Enter o clic en un resultado hace volar la cámara a la estrella y muestra su tooltip;
  - filtros: puntaje mínimo (0–100, de 5 en 5), empresa (select con las empresas presentes) y tipo (todas, práctica o junior);
  - lista de nubes con nombre y cantidad: un clic vuela al centroide.
- **Detalle:** clic en una estrella abre `JobDetail` (variante lateral) con feedback y guardar, igual que en Inicio. Si la oferta tiene duplicados, el detalle muestra "+N publicaciones casi idénticas" con sus enlaces.

### 2.5 Pestaña Habilidades
- **Datos:** `GET /api/skills-graph`; las habilidades con grado 0 van a la lista de chips, igual que en 2D.
- **Layout:** `graph3d.ts`, con fuerzas de enlace, carga −60, centro y colisión.
- **Habilidades:** estrellas de tamaño 0.8 + 0.8·grado/máx con etiqueta. Las que tienes van en plata y las que faltan en `#E0626F` al 80 %.
- **Ofertas:** estrellas pequeñas (0.35); blancas si el puntaje es ≥ 60 y azules si no.
- **Aristas:** líneas tenues en `#CBD5E1` al 15 %.
- **Interacción:**
  - hover sobre una habilidad resalta sus ofertas y aristas (`highlight`);
  - clic en una habilidad lista sus ofertas en el panel, por puntaje;
  - clic en una oferta abre `JobDetail`;
  - el buscador encuentra habilidades y ofertas.

### 2.6 Enlaces y top
- **Inicio:** botón **"Explorar en 3D"** (`Link` a `/universo`) en la esquina del mapa semántico.
- **Perfil:** botón **"Ver en 3D"** (`Link` a `/universo?vista=habilidades`) sobre el grafo.
- **`JobCard`:** si `duplicados.length > 0`, muestra "+N publicación casi idéntica" en mono, con los enlaces "↗ 2", "↗ 3"…
- **Navegación:** `/universo` no aparece en el menú lateral; se llega desde los botones. Tiene un botón "← Volver".

## 3. Errores y estados
- **Cargando:** el fondo de estrellas lejanas aparece de inmediato y el panel dice "Cargando el universo…".
- **Error de API:** el mensaje del backend con "Reintentar"; un 404 sin perfil muestra el `EmptyState` "sin-perfil" con enlace a Perfil.
- **Sin ofertas:** el mensaje "Todavía no hay ofertas para mostrar en el universo." con el fondo visible.

## 4. Pruebas

**Backend:**
- `project3d`:
  - el radio igual al de 2D;
  - el signo determinista sin importar el orden de las filas;
  - menos de 4 ofertas en la espiral;
  - el caso vacío.
- `clusters`: determinista, `k` según `n` e índices válidos.
- `cluster_names`: las 2 más frecuentes, el desempate y "Grupo N".
- `duplicate_groups`:
  - misma empresa con ≥ 0.99 se agrupa;
  - empresa distinta no;
  - 0.98 no;
  - cadenas A~B~C;
  - la elección del representante.
- `/api/universe`: 404, vacío, filtros iguales a `/api/map`, duplicados ocultos con su lista, nubes con centroide.
- `/api/top` agrupa; `/api/jobs` marca sin ocultar; el feedback alcanza al grupo.

**Frontend:**
- `stars`: tamaños y colores por puntaje, filtradas con opacidad baja, escala ×6.
- `search`: acentos, prefijo primero, máximo 8.
- `camera`: `flyTarget` y `ease` en los extremos.
- `graph3d`: determinista y dentro de un radio razonable.
- `Universe` con la escena falsa:
  - carga y llama `setStars`;
  - buscar y Enter llama `flyTo` con la posición de esa estrella;
  - el filtro cambia la opacidad;
  - clic simulado (`onPick`) abre `JobDetail`;
  - la pestaña Habilidades llama `setLabels` con los nombres;
  - sin WebGL, el mensaje con enlace;
  - con movimiento reducido, `createScene` recibe `reducedMotion: true`.
- `JobCard` muestra "+1 publicación casi idéntica".
- Inicio y Perfil tienen los enlaces a `/universo`.

**Manual:** en el navegador integrado con el panel visible, en escritorio y a 375 px:
- rotar, zoom, autorrotación, vuelo al buscar, tooltip y detalle;
- pestaña Habilidades;
- que no haya errores en consola;
- que las ofertas duplicadas de HPE aparezcan agrupadas.

## 5. Fuera de alcance
- Realidad virtual, postprocesado (bloom real) y física en vivo.
- Guardar la posición de la cámara entre visitas.
- Cambios en el matching o en la ingesta.
