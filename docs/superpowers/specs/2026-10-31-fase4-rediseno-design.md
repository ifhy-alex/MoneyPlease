# Fase 4 — Rediseño "Medianoche y plata" + arreglos pendientes

**Fecha:** 2026-10-31 · **Rama:** `fase4-rediseno`

## Por qué

El dashboard de la Fase 3 funciona, pero al usuario no le gusta cómo se ve. Lo encuentra simple, con poco arte y con colores (crema/dorado y azul plano) que lo hacen parecer "una app barata". Quiere una mezcla de **tech premium oscuro** (Linear, Raycast) y **arte generativo** con estética **tecnológica/algorítmica**, nada de naturaleza: ni jardín, ni río, ni cielo, ni constelación. De paso se cierran los defectos menores que quedaron diferidos en la revisión de la Fase 3.

**Listo cuando:**
- Las cuatro vistas usan la identidad nueva.
- Inicio abre con el mapa semántico y Perfil con el grafo de habilidades.
- Ya no queda ninguna pieza con metáfora de naturaleza.
- Los 12 arreglos tienen su prueba.
- Las suites de backend y frontend pasan y el build compila.
- La revisión en navegador a 360 px y en escritorio no muestra scroll horizontal ni texto ilegible.

## Decisiones del usuario

| Tema | Decisión |
|---|---|
| Dirección | Tech premium oscuro + arte generativo |
| Paleta | Medianoche y plata |
| Modo claro | Se elimina; solo oscuro |
| Arte | Pieza protagonista en Inicio + ambiente en todo |
| Estilo del arte | Algorítmico/tech, sin naturaleza |
| Pieza de Inicio | Mapa semántico |
| Pieza de Perfil | Grafo de habilidades |

## 1. Identidad visual

### Tokens (`frontend/src/theme.css`, `lib/tokens.ts`)
Solo un tema; se eliminan el bloque claro, el selector de tema y la preferencia guardada.

| Token | Valor | Uso |
|---|---|---|
| `--bg` | `#04060F` | Fondo de página |
| `--glass` | `rgba(255,255,255,.045)` | Superficie de tarjetas |
| `--glass-strong` | `rgba(255,255,255,.07)` | Hover, diálogos |
| `--line` | `rgba(255,255,255,.09)` | Bordes |
| `--line-strong` | `rgba(255,255,255,.16)` | Bordes en hover/foco |
| `--text` | `#F1F5F9` | Texto principal |
| `--muted` | `#7A8399` | Texto secundario |
| `--silver` | `#CBD5E1` | Acento: anillos, chips, enlaces |
| `--glow` | `#2547B8` | Luz azul: solo arte y brillos de fondo |
| `--ok` | `#5FB89A` | Estado positivo (apagado) |
| `--danger` | `#E0626F` | Error/destructivo (apagado) |

- El texto y el acento sobre `--bg` y sobre `--glass` cumplen AA. La prueba existente de `lib/contrast.ts` se actualiza a estos pares.
- Las tarjetas son vidrio: fondo `--glass`, borde 1px `--line`, `backdrop-filter: blur(14px)`, radio 14px. Un brillo radial sigue al puntero sobre el borde mediante las variables CSS `--mx/--my`. Con movimiento reducido el brillo queda fijo.
- **Tipografía:** Geist para la interfaz y Geist Mono para lo técnico (puntajes, fechas, IDs, chips de habilidades). Ambas se empaquetan con `@fontsource-variable/geist` y `@fontsource-variable/geist-mono`. Se quitan los enlaces a Google Fonts y Fraunces, así que la app ya no depende de internet para las fuentes. Los números usan `font-variant-numeric: tabular-nums`. Jerarquía: 28/20/15/13 px, pesos 400/500/600.

### Ambiente (`decor/`)
- **`AmbientField`** reemplaza a `NightGradient` y `FlowField`. Es un canvas fijo detrás de todo, con un campo de flujo de partículas (simplex-noise) en `--glow` y `--silver` con alfas bajos, más un halo radial azul arriba.
  - Va a 30 fps como máximo y con DPR limitado a 2.
  - Se pausa cuando la pestaña está oculta (`visibilitychange`).
  - Con movimiento reducido dibuja un solo cuadro estático.
- **`Grain`** se queda, más sutil (opacidad 0.035).
- **`EmptyState`** cambia las ilustraciones por patrones generativos deterministas por semilla: retícula de puntos, líneas de contorno y Truchet. Uno por tipo de vacío; los textos se mantienen.

## 2. Piezas de arte

Todas usan canvas o SVG con la paleta nueva, son deterministas dado los datos (las semillas salen de los IDs), respetan el movimiento reducido y separan la lógica (`*Layout.ts`, probada) del dibujo (`*.tsx`).

| Vista | Se elimina | Se crea |
|---|---|---|
| Inicio | `DailySky`, `sky.ts` | `SemanticMap.tsx` + `mapLayout.ts` |
| Perfil | `Constellation.tsx`, `constellationLayout.ts` | `SkillGraph.tsx` + `skillGraphLayout.ts` |
| Perfil | `ProfileGlyph` (se rehace) | `Fingerprint.tsx` (reusa la semilla de `glyph.ts`) |
| Postulaciones | `Garden.tsx`, `gardenLayout.ts` | `Pipeline.tsx` + `pipelineLayout.ts` |
| Explorar | `OfferRiver` (se reestiliza) | `SignalFlow.tsx` (reusa `river.ts`) |
| Celebración | `Starfall.tsx` | `ParticleBurst.tsx` |

### 2.1 Mapa semántico (Inicio)
- **Datos:** `GET /api/map` (ver §3.1).
- **Dibujo:**
  - El perfil va en el centro, con dos anillos concéntricos.
  - Cada oferta es un punto, con radio de 1.5 a 3.5 px según el puntaje.
  - El color depende del puntaje: sin evaluar, `--glow` al 55%; menos de 60, `--silver` al 60%; 60 o más, `--text` con halo.
  - Las 6 mejores llevan líneas finas hacia el centro.
  - Animación de entrada: los puntos salen del centro a su posición en 900 ms. Después hay una deriva sutil de ±1.5 px. Con movimiento reducido no hay ninguna de las dos.
- **Interacción:**
  - Al pasar el puntero se busca el punto más cercano dentro de 14 px (en `mapLayout.ts`) y aparece un tooltip de vidrio con título, empresa y puntaje.
  - El clic abre el `JobDetail` existente. En pantallas táctiles, el primer toque muestra el tooltip y el segundo abre el detalle.
  - **Teclado:** el canvas tiene `role="img"` con un resumen ("312 ofertas; 9 con puntaje ≥ 60"). Debajo sigue la lista del top con las tarjetas, que es la vía accesible.
- **Tamaño:** alto de 420 px en escritorio y 300 px a menos de 640 px de ancho. El ancho es el del contenedor, sin scroll horizontal.
- **Layout:** `mapLayout.ts` traduce las coordenadas (x, y) de la API (entre −1 y 1) a píxeles, con un margen de 24 px. También hace el hit-test (`nearestPoint`) y la escala de radio y color por puntaje.

### 2.2 Grafo de habilidades (Perfil)
- **Datos:** `GET /api/skills-graph` (ver §3.2).
- **Dibujo:**
  - Las habilidades son círculos con borde `--silver`; su radio va de 5 a 10 px según el grado (cuántas ofertas las piden).
  - Las habilidades que **no tienes** pero piden las ofertas son círculos discontinuos en `--danger` apagado.
  - Las ofertas son cuadrados de 3 px; las de puntaje 60 o más van en `--text`.
  - Las aristas son líneas de 0.5 px.
  - Las etiquetas de las habilidades van en Geist Mono de 11 px.
- **Layout:** `skillGraphLayout.ts` usa d3-force con semilla fija y 300 iteraciones calculadas de una vez, no en vivo. Así el resultado es determinista y se puede probar.
- **Interacción:** al pasar sobre una habilidad se resaltan sus aristas y sus ofertas, y se atenúa el resto. Al hacer clic en una oferta se abre su detalle.

### 2.3 Huella (Perfil)
`Fingerprint.tsx` reemplaza al glifo floral: son líneas radiales y arcos concéntricos tipo código circular, generados con la semilla de `glyph.ts`. Cada área de habilidad (de `/api/profile` → `areas`) controla la longitud de un sector.

### 2.4 Pipeline (Postulaciones)
Sustituye al jardín como vista por defecto; el tablero kanban se mantiene en la otra pestaña.
- Hay 5 columnas de etapas: guardada → aplicada → entrevista → oferta, más una lateral de rechazada o descartada.
- Cada postulación es un nodo.
- Hay curvas Bézier que unen las etapas por las que ya pasó cada postulación.
- Los nodos que necesitan seguimiento laten, salvo con movimiento reducido.
- `pipelineLayout.ts` reparte los nodos por columna y ordena por fecha.
- Cada nodo es un `button` con `aria-label` "Editar {título}". Así se mantiene la accesibilidad que ya tenían las plantas del jardín.

### 2.5 Flujo de ingesta (Explorar)
Se mantiene el streamgraph (`river.ts` con `stackOffsetWiggle`). El dibujo pasa de capas rellenas a líneas finas: el contorno de cada capa con un relleno al 8%, más una retícula horizontal tenue y las etiquetas de los ejes en mono.

### 2.6 Estallido de partículas
`ParticleBurst.tsx` reemplaza a `Starfall` y se dispara al mover una postulación a *entrevista* u *oferta*. Son 60 partículas radiales desde el centro de la tarjeta, que se desvanecen en 1.2 s. Con movimiento reducido no se muestra (la prueba actual se mantiene, con un `data-testid` nuevo).

## 3. Backend

### 3.1 `GET /api/map`
Respuesta:
```json
{ "total": 312, "puntos": [ { "job_id": 1, "titulo": "...", "empresa": "...", "x": 0.12, "y": -0.4,
  "similitud": 0.81, "puntaje": 88, "etiqueta": null } ] }
```

**Qué ofertas entran:**
- Activas, con embedding, que pasan los filtros duros del perfil activo (`matching/filters.py`) y que no están marcadas `no_interesa`.
- Como máximo 300: las más cercanas al perfil por distancia coseno.

**Proyección** (`moneyplease/projection.py`, función pura con numpy):
1. Se calcula `s = cos(job, perfil)`. Como los vectores están normalizados, es el producto punto.
2. El radio es `r = (s_max − s) / (s_max − s_min)`, en [0, 1]. Si todas tienen la misma similitud, `r = 0.5`.
3. El ángulo sale de un PCA sobre los residuos `v − s·p`, que es la parte de cada oferta que no se explica por el perfil. Se usan las 2 primeras componentes con `numpy.linalg.svd`, se fija el signo para que la carga de mayor valor absoluto sea positiva, y `θ = atan2(c2, c1)`. Con menos de 3 ofertas, θ se reparte uniformemente por `job_id`.
4. `x = r·cos θ`, `y = r·sin θ`.

**Otros datos y errores:**
- `puntaje` y `etiqueta` salen del match con el perfil activo y del feedback, si existen.
- Si no hay perfil, responde 404 "Todavía no hay perfil guardado".
- En modo demo funciona con los vectores sembrados.

### 3.2 `GET /api/skills-graph`
Respuesta:
```json
{ "habilidades": [ { "nombre": "Java", "nivel": "avanzado", "area": "backend", "grado": 7, "tiene": true } ],
  "ofertas": [ { "job_id": 1, "titulo": "...", "empresa": "...", "puntaje": 88 } ],
  "aristas": [ { "habilidad": "Java", "job_id": 1 } ] }
```

- **Ofertas:** las 40 mejores visibles (`top_matches(..., hide_rejected=True)`).
- **Aristas:** habilidades detectadas en el título y la descripción de cada oferta con `skill_areas.find_skill`. Hay arista si el perfil tiene esa habilidad, o si es una de las 8 habilidades que más piden las ofertas y el perfil no tiene (`tiene=false`).
- **Errores:** sin perfil responde 404, y sin matches devuelve las listas vacías.

### 3.3 Mantenimiento de Workday
`ingest/connectors/workday.py` detecta cuando la respuesta redirige a `community.workday.com/maintenance-page`, o cuando no es JSON y su `Location` o URL final contiene `maintenance`. En ese caso levanta un error con el mensaje "Workday en mantenimiento". El resumen de la ingesta lo muestra así, sin `JSONDecodeError`.

## 4. Arreglos diferidos

Cada uno lleva una prueba que falla primero.

| # | Defecto | Arreglo |
|---|---|---|
| 1 | Gemini devuelve un ítem de más de 120 caracteres o más de 5 ítems, y la evaluación falla (`string_too_long`) | En `matching/score.py`, un `BeforeValidator` recorta los ítems a 120 caracteres (con "…"), las listas a 5 y `resumen` a 300 |
| 2 | Aparece "Ninguna brecha" (o "N/A", "ninguna", "sin brechas") como brecha | Se filtran esos valores al validar `brechas` (sin distinguir mayúsculas ni acentos) |
| 3 | Dos feedback simultáneos sobre la misma oferta dan 500 | Upsert con `ON CONFLICT` en `job_labels` |
| 4 | `/api/top?n=-1` da 500 | `n: int = Query(10, ge=1, le=50)` → 422 |
| 5 | `PUT /api/profile` guarda el `cv_texto` de la versión anterior aunque haya un CV nuevo importado | Usar `private/cv.txt` si existe y es más reciente que la versión activa; si no, el de la versión activa |
| 6 | Guardar el perfil no refresca Inicio | Invalidar `top`, `insights`, `map` y `skills-graph` al guardar |
| 7 | El feedback en Explorar no es optimista | Mismo patrón optimista con deshacer que Inicio |
| 8 | Los diálogos no tienen `aria-modal`, Escape ni foco | Componente `Dialog` común: `role="dialog"`, `aria-modal`, cierra con Escape, atrapa el foco y lo devuelve al cerrar. Lo usan `JobDetail` y `ApplicationEditor` |
| 9 | Borrar una postulación no pide confirmación | `ConfirmDialog` ("¿Borrar esta postulación?", botón destructivo) |
| 10 | Modo demo sin sembrar da 500 | Si faltan las tablas o los datos, 503 con "Modo demo sin datos: corre `demo seed`" |
| 11 | Workday en mantenimiento aparece como `JSONDecodeError` | §3.3 |
| 12 | No hay selector de tema en el celular | Desaparece al quitar el modo claro (§1) |

## 5. Errores y estados

- Mapa o grafo cargando: esqueleto de vidrio con una retícula de puntos tenue.
- Error de la API: tarjeta de vidrio con el mensaje del backend y un botón "Reintentar".
- Sin perfil: el mapa y el grafo muestran el `EmptyState` correspondiente, con enlace a Perfil.
- Pocos datos (menos de 3 ofertas): el mapa se dibuja igual (§3.1, paso 3).

## 6. Pruebas

**Backend (pytest):**
- `projection`: radio y ángulo con vectores sintéticos, signo determinista, caso de similitud constante y caso con menos de 3 ofertas.
- `/api/map`: filtros duros, excluye `no_interesa`, máximo 300, 404 sin perfil.
- `/api/skills-graph`: aristas, habilidades faltantes (máximo 8), 404 y listas vacías.
- Recorte y filtro de `score.py`, `ON CONFLICT` del feedback, validación de `n`, `cv_texto`, demo sin sembrar y mantenimiento de Workday con respx.

**Frontend (Vitest):**
- `mapLayout`: escala, `nearestPoint` y radio/color por puntaje.
- `skillGraphLayout`: determinismo con la misma semilla y nodos dentro de los límites.
- `pipelineLayout`: columnas y orden.
- `Dialog`: Escape y retorno del foco.
- `ConfirmDialog` en el borrado.
- Feedback optimista en Explorar.
- Invalidación al guardar el perfil.
- Movimiento reducido: el estallido no aparece y el ambiente queda estático.
- Las pruebas de vistas existentes se actualizan a los nombres nuevos.

**Contraste:** los pares de tokens nuevos cumplen AA.

**Manual:** en el navegador integrado, las cuatro vistas a 360 px y en escritorio, con datos reales en solo lectura y con DEMO_MODE para las interacciones.

## 7. Fuera de alcance

- El correo diario (3b).
- Nuevas fuentes de ofertas.
- Cambios al algoritmo de matching, aparte del recorte y el filtro de §4.
- Modo claro.
- Visualización 3D o WebGL: todo es canvas 2D o SVG.
