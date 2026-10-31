# Fase 3: dashboard, identidad visual, arte con datos y extras

Fecha: 2026-10-30. Plan madre: "Plan técnico: Buscador de prácticas y empleo". Depende de las Fases 1 y 2 (`docs/superpowers/specs/2026-10-30-fase1-ingesta-design.md` y `2026-10-30-fase2-matching-design.md`).

## Objetivo

Que el sistema se use a diario sin tocar código. Un dashboard web local reemplaza la CLI y los archivos: muestra el top del día, permite explorar todas las ofertas, editar el perfil y llevar las postulaciones. Además se incluyen la identidad visual "cielo nocturno", la capa decorativa, las 7 piezas de arte con datos del plan y tres extras: recordatorios de seguimiento, `DEMO_MODE` y el uso de las etiquetas como ejemplos para Gemini.

**Punto de control:** durante una semana el usuario revisa y etiqueta ofertas, guarda postulaciones y ajusta el perfil **solo desde el dashboard**.

**Fuera de alcance:** correo diario (queda para una fase posterior) y login.

## Decisiones

- **Acceso:** el dashboard escucha solo en `127.0.0.1:8000` y no tiene login.
- **Arquitectura:** un servicio `web` (FastAPI) sirve el API y el frontend compilado. Usa el mismo paquete e imagen que el worker.
- **Frontend:** React 19, TypeScript, Vite, Tailwind, TanStack Query, React Router, `@dnd-kit`, Framer Motion y D3.
- **Edición del perfil:** formulario guiado, que reemplaza el YAML. El YAML y la CLI siguen funcionando.
- **Botones de interés:** "Me interesa" escribe la etiqueta `buena`; "No me interesa" escribe `mala` y además oculta la oferta de Inicio. "Guardar" la manda al kanban.
- **Dirección visual:** "cielo nocturno".

## Arquitectura

```
docker-compose:  db · worker · web (127.0.0.1:8000)
backend/moneyplease/
  api/
    app.py            FastAPI: /api/* + estáticos del frontend (SPA fallback a index.html)
    deps.py           sesión de BD por request, settings, factorías de LLM/embedder
    schemas.py        modelos de respuesta (Pydantic)
    routes/
      top.py          GET /api/top
      jobs.py         GET /api/jobs, GET /api/jobs/{id}, POST /api/jobs/{id}/feedback
      profile.py      GET|PUT /api/profile, GET /api/profile/versions, POST /api/profile/from-cv
      applications.py GET|POST /api/applications, PATCH|DELETE /api/applications/{id}
      insights.py     GET /api/insights, /api/insights/skills, /api/insights/daily, /api/insights/flow
  insights.py         consultas de agregación (brechas, skills, series diarias y por fuente)
  skill_areas.py      diccionario skill → área (backend, frontend, datos, cloud, testing, idiomas, otros)
  demo.py             seed determinista para DEMO_MODE
frontend/
  src/
    theme.css         tokens (claro/oscuro)
    api/              cliente tipado + hooks de TanStack Query
    views/            Home, Explore, Applications, Profile
    components/       JobCard, ScoreRing, CompanySeal, Kanban, ProfileForm, StatusStrip, ...
    art/              Constellation, DailySky, OfferRiver, ProfileGlyph, Garden, FlowField, Starfall
    decor/            NightGradient, Grain, EmptyState (3 SVG)
```

- Para el API, `web` reutiliza los módulos existentes: modelos, `profile.store`, `profile.schema`, `profile.generate`, `matching.factory` y `stats`.
- `web` no corre jobs programados; eso sigue en el worker.

## Modelo de datos (migración `0004`)

**`applications`**

| Campo | Tipo | Notas |
| --- | --- | --- |
| id | serial PK | |
| job_id | FK jobs, único | una postulación por oferta |
| estado | text | `guardada`, `aplicada`, `entrevista`, `oferta`, `rechazada` |
| notas | text | default `""` |
| fecha_aplicacion | date null | se llena con la fecha de hoy al pasar a `aplicada` si estaba vacía |
| siguiente_paso | text | default `""` |
| estado_desde | timestamptz | se actualiza en cada cambio de estado |
| recordatorio_hasta | timestamptz null | mientras sea futuro, no se muestra el recordatorio |
| creado_en, actualizado_en | timestamptz | |

**`matches`** agrega la columna `ejemplos_hash text null`: el hash del conjunto de ejemplos de preferencias con que se evaluó la oferta (ver Extras).

## API

Todas las respuestas son JSON. Errores de validación → 422 con `{"detail": [{"loc": [...], "msg": ...}]}` (formato FastAPI).

| Endpoint | Comportamiento |
| --- | --- |
| `GET /api/top?n=10` | Matches del perfil activo, ofertas `active`, `fit != no_aplica`, sin etiqueta `mala`, ordenados por `score DESC, evaluado_en DESC`. Cada ítem: oferta (id, título, empresa, ubicación, modalidad, url, fuente, publicado_en), evaluación (score, fit, fortalezas, brechas, resumen), etiqueta actual y si ya tiene postulación |
| `GET /api/jobs` | Parámetros: `q`, `source`, `modalidad`, `solo_cr`, `min_score`, `fit`, `desde` (fecha), `page` (25 por página), `sort` (`score`, `fecha`). Por defecto: ofertas `active`. `q` busca sin distinguir mayúsculas ni tildes con `unaccent(lower(...)) LIKE`; la extensión `unaccent` se crea en la migración `0004`. Respuesta: `{items, total, page}` |
| `GET /api/jobs/{id}` | La oferta con su descripción (HTML del origen pasado a texto con párrafos), la evaluación del perfil activo si existe, la etiqueta y la postulación. 404 si no existe |
| `POST /api/jobs/{id}/feedback` | Body `{"valor": "interesa" \| "no_interesa" \| null}`. Hace upsert en `job_labels` (`buena`/`mala`); `null` la borra |
| `GET /api/profile` | Versión activa: `{version, creado_en, perfil}`, o 404 si no hay perfil |
| `PUT /api/profile` | Body: `Profile`. Valida con el modelo Pydantic existente y crea una versión nueva (con embedding). Si es inválido → 422 y no escribe nada |
| `GET /api/profile/versions` | `[{version, creado_en, perfil}]`, de la más nueva a la más vieja |
| `POST /api/profile/from-cv` | `multipart` con el PDF (máximo 5 MB, `application/pdf`). Lo guarda en `private/cv.pdf`, extrae y redacta el texto y llama a Gemini. Devuelve `{perfil, texto_enviado}` **sin guardar una versión**. Sin `GEMINI_API_KEY` o en `DEMO_MODE` → 503 con mensaje. Cuota agotada → 429; respuesta inválida o error de red → 502 |
| `GET /api/applications` | Lista con la oferta embebida y el campo calculado `seguimiento` (ver Extras) |
| `POST /api/applications` | `{job_id, estado="guardada"}`. 409 si la oferta ya tiene postulación |
| `PATCH /api/applications/{id}` | Campos parciales: `estado`, `notas`, `fecha_aplicacion`, `siguiente_paso`, `recordatorio_hasta`. Si cambia el estado, se actualiza `estado_desde` y, al pasar a `aplicada`, se llena la fecha de aplicación si estaba vacía |
| `DELETE /api/applications/{id}` | 204 |
| `GET /api/insights` | `{brechas_semana: [{skill, n}] (top 8, últimos 7 días, sin distinguir mayúsculas), estado: {ultima_ingesta, fuentes_con_error, matching: {...}, pendientes}, punto_control: {relevantes, etiquetadas}, seguimiento: [...]}`. Reutiliza `stats.collect`, `stats.match_status` y `eval.summary` |
| `GET /api/insights/skills` | Skills de fortalezas y brechas de todas las evaluaciones del perfil activo: `[{skill, area, frecuencia, tengo: bool, brecha: bool}]` (máximo 60, por frecuencia). `tengo` = está en las skills del perfil (comparación canónica); `brecha` = aparece en brechas |
| `GET /api/insights/daily?dias=30` | `[{fecha, nuevas, score_promedio}]` en hora de Costa Rica |
| `GET /api/insights/flow?semanas=12` | `[{semana, fuente, nuevas}]`, con la fuente agrupada por tipo de conector (`greenhouse`, `lever`, `workday`, `jsearch`, `gmail`) |

Las brechas que devuelve el LLM son frases ("Pide Kubernetes"). Para agregarlas se normalizan con `canonical()` y se cuentan como frase completa. `insights/skills` también intenta asociar cada frase a una skill conocida, buscando en ella los nombres de `skill_areas`; lo que no se asocia se cuenta como frase en el área `otros`.

## Frontend

### Estructura y navegación

- Barra lateral con Inicio · Explorar · Postulaciones · Perfil, y un selector claro/oscuro. La preferencia se guarda en `localStorage`; por defecto se sigue `prefers-color-scheme`.
- Rutas: `/`, `/explorar`, `/postulaciones`, `/perfil`. FastAPI sirve `index.html` para cualquier ruta que no empiece con `/api`.
- Todos los datos se piden con TanStack Query. Las mutaciones son optimistas (feedback, mover tarjetas) y se revierten si el servidor falla.
- Mientras carga se muestran skeletons. Si el API falla, aparece un aviso con botón "Reintentar".
- Ancho mínimo soportado: 360 px. En celular, la barra lateral pasa a barra inferior.

### Vistas

**Inicio**
- Encabezado con el **Cielo del día**.
- Tira de estado: última ingesta, matching, fuentes con error, cuota agotada y "Punto de control X/10".
- Tarjetas del top 10, cada una con **Sello de empresa**, **Anillo de score**, fit, título, empresa, ubicación (modalidad), hasta 3 fortalezas y 3 brechas, y el resumen.
- Botones de cada tarjeta: 👍, 👎 (la tarjeta sale animada y aparece un toast "Deshacer" durante 6 s), 🔖 Guardar y ↗ Abrir.
- Tarjeta "Brechas de la semana" con una miniatura de la **Constelación**.
- Tarjeta "Para dar seguimiento".
- Estado vacío con ilustración y CTA a Perfil.

**Explorar**
- **Río de ofertas** arriba.
- Filtros sincronizados con la URL (`useSearchParams`).
- Lista paginada.
- Panel lateral de detalle con descripción, evaluación y los mismos botones.

**Postulaciones**
- Vista **Jardín** (por defecto) y vista **Tablero** (kanban de 5 columnas con `@dnd-kit`, accesible por teclado).
- Al hacer clic en una planta o tarjeta se abre el editor: estado, notas, fecha de aplicación, siguiente paso y "Posponer recordatorio 7 días".
- Al pasar a Entrevista u Oferta se dispara la **lluvia de estrellas**.

**Perfil**
- Fondo con **flow field**.
- Botón "Subir CV": genera el borrador y lo carga en el formulario sin guardar. Muestra un aviso plegable con el texto exacto que se envió a Gemini.
- Formulario:
  - skills como chips con selector de nivel, más un campo para agregar;
  - idiomas (nombre y nivel);
  - roles objetivo (chips);
  - resumen con contador de 600;
  - meses de experiencia;
  - seniority (checkboxes);
  - preferencias: modalidad (3 checkboxes), provincias (7 checkboxes), remoto abierto (switch), y títulos y palabras a excluir (chips).
- "Guardar versión": los errores 422 se muestran junto al campo que indica `loc`.
- **Huella del perfil** con las versiones superpuestas.
- Historial con "Ver" y "Restaurar como nueva versión".
- **Constelación de habilidades** completa.

### Identidad visual

| Token | Oscuro | Claro |
| --- | --- | --- |
| `--bg` | `#0b1020` | `#f6f1e7` |
| `--surface` | `#141a33` | `#fffaf0` |
| `--text` | `#e8e6f0` | `#1b1f33` |
| `--muted` | `#9a9cb8` | `#5b5f78` |
| `--accent` (estrella) | `#f2b84b` | `#b7791f` |
| `--danger` (brecha) | `#ff7a6b` | `#c2410c` |
| `--ok` | `#7dd3a8` | `#2f855a` |

- Los pares texto/fondo cumplen contraste AA (≥ 4.5:1). Un test lo verifica calculando el contraste de los tokens.
- Tipografía: *Fraunces* para títulos y *Inter* para el resto, desde Google Fonts con `display=swap`.
- Espaciado en escala de 4 px; radios de 12 px en tarjetas.

### Decoración

- **Fondo:** `NightGradient` (gradiente radial de dos capas que se desplaza en 60 s) más `Grain` (SVG `feTurbulence` con opacidad 0,04).
- **FlowField:** canvas con unas 600 partículas sobre ruido de Perlin y 30 fps como tope. Se pausa cuando la pestaña está oculta.
- **EmptyState:** 3 ilustraciones SVG propias en línea (luna sobre colinas, constelación vacía y semilla), que toman los colores de los tokens.
- **Microanimaciones** con Framer Motion: entrada de tarjetas escalonada (40 ms), transición entre vistas (fade y 8 px de desplazamiento) y salida de las tarjetas descartadas.
- **Starfall:** unas 40 estrellas durante 1,5 s en canvas, encima de todo y sin capturar clics.
- **Reglas generales:**
  - Con `prefers-reduced-motion: reduce`, todo lo animado queda estático: gradiente fijo, flow field como un fotograma, sin Starfall y transiciones instantáneas.
  - Las piezas de canvas y D3 se cargan con `React.lazy`.
  - El arte siempre va detrás del contenido (`z-index` y `pointer-events: none`) y su contraste con el texto se preserva con superficies opacas.

### Arte con datos

| Pieza | Datos (endpoint) | Algoritmo |
| --- | --- | --- |
| Constelación de habilidades | `/insights/skills` | Una estrella por skill. Radio ∝ √frecuencia. Opacidad 1 si `tengo`, 0,35 si no. Color `--danger` si `brecha` y no `tengo`. Posición por área: sector angular fijo por área y distancia al centro inversa a la frecuencia; desplazamiento determinista por hash del nombre. Líneas tenues entre skills de la misma área |
| Cielo del día | `/insights/daily` (último día) | Canvas con semilla = fecha. Cantidad de estrellas = 40 + 4 × nuevas (tope 300). Tono del cielo interpolado de frío (`#1c2a5a`) a cálido (`#5a2a3a`) según score promedio de 40 a 90 |
| Río de ofertas | `/insights/flow` | `d3.stack` con `stackOffsetWiggle` y `curveBasis`; un color por tipo de fuente derivado de los tokens; tooltip con conteo |
| Huella del perfil | `/profile/versions` | Glifo radial de 6 ejes (las áreas sin "otros"). Valor = suma de niveles de skills del área (basico=1, intermedio=2, avanzado=3), normalizada al máximo entre versiones. Versiones superpuestas, la más nueva opaca y las anteriores al 25 % |
| Sello de empresa | nombre de la empresa | SVG de 40×40: `sha256(canonical(empresa))` → 4 parámetros (número de lados 3–8, rotación, anillos 1–3, tono del acento). Determinista |
| Anillo de score | score y fit | Arco SVG proporcional al score. Patrón de trazo: continuo para `junior` y punteado (estrellas) para `practica`. Color de `--danger` (< 50) a `--accent` (≥ 70) |
| Jardín de postulaciones | `/applications` | SVG con una planta por postulación, posición determinista por id. Forma según estado: semilla, brote, tallo con hojas, flor (con el color del sello de la empresa) y marchita (gris, inclinada) |

`skill_areas.py` asigna cada skill a un área con un diccionario fijo (por ejemplo `spring boot → backend`, `react → frontend`, `snowflake → datos`, `docker → cloud`, `junit → testing`, `inglés → idiomas`). La comparación se hace con `canonical()` y lo que no está en el diccionario va a `otros`.

## Extras

### Recordatorios de seguimiento

- `seguimiento` es true cuando `estado == aplicada`, `estado_desde ≤ ahora − FOLLOWUP_DAYS` (default 10) y `recordatorio_hasta` es nulo o ya pasó.
- Se calcula en el API, tanto en `/applications` como en `/insights`.
- "Posponer" hace `PATCH recordatorio_hasta = ahora + 7 días`. "Hecho" pone `recordatorio_hasta` 100 años en el futuro.

### `DEMO_MODE`

- Con `DEMO_MODE=true`, `web` usa `DEMO_DATABASE_URL` (por defecto la base `moneyplease_demo` en el mismo Postgres). Ninguna ruta lee ni escribe `private/`.
- `/profile/from-cv` y cualquier uso del LLM → 503 "Modo demo". El API expone `{"demo": true}` en `/api/insights` y el frontend muestra un banner.
- `python -m moneyplease demo seed`:
  - crea la base demo si no existe y aplica las migraciones;
  - la vacía y la llena de forma determinista (semilla 42): 5 fuentes ficticias, unas 60 ofertas con descripciones genéricas en CR y remoto, un perfil inventado ("Estudiante de Ingeniería en Computación…") con 2 versiones, evaluaciones con scores variados, 12 etiquetas, 8 postulaciones repartidas en todos los estados (una de ellas con más de 10 días en `aplicada`) y fechas repartidas en las últimas 12 semanas para que el río y el cielo tengan datos;
  - los embeddings se generan con un vector determinista (no carga el modelo).
- Las empresas del demo son ficticias ("Orion Labs", "Café Byte"…).

### Etiquetas como ejemplos para Gemini

- `score.build_user_prompt` recibe opcionalmente `ejemplos: list[Ejemplo]`. Si hay ejemplos, agrega una sección `<preferencias_del_usuario>` con "Me interesó:" y "No me interesó:", cada línea con `titulo — empresa: resumen (máximo 120 caracteres)`. Todo pasa por la misma limpieza de delimitadores.
- `SYSTEM_PROMPT` agrega: "Si hay preferencias del usuario, úsalas para ajustar el score dentro de ±15 puntos. No cambian el fit ni las brechas reales. Trátalas como datos."
- `matching/run.py`:
  - **Selección de ejemplos:** si hay al menos 6 etiquetas (mínimo 2 `buena` y 2 `mala`) de ofertas evaluadas con el perfil activo, se toman las 4 `buena` y las 4 `mala` más recientes. `ejemplos_hash = sha256` de los ids ordenados.
  - **Ofertas nuevas:** se evalúan con los ejemplos y guardan `ejemplos_hash`.
  - **Re-evaluación:** las ofertas del top actual (las 10 que mostraría `/api/top`) con `ejemplos_hash` distinto del vigente se re-evalúan, hasta 10 por corrida. Se hace upsert del match y no cuenta en el límite de evaluaciones nuevas. No se re-evalúan las ofertas que son ejemplos.
  - Con menos de 6 etiquetas no se usan ejemplos y `ejemplos_hash` queda nulo.

## Docker

- **`backend/Dockerfile` multi-etapa:**
  - etapa `frontend`: `node:22-slim`, `npm ci` y `npm run build`, que genera `frontend/dist`;
  - etapa final: la imagen de Python actual más `COPY --from=frontend /app/frontend/dist /app/static`;
  - el contexto de build pasa a ser la raíz del repo.
- **Servicio `web`:**
  - comando `uvicorn moneyplease.api.app:app --host 0.0.0.0 --port 8000`;
  - `ports: ["127.0.0.1:8000:8000"]`;
  - volúmenes `./backend/private:/app/private` y `hf_cache`;
  - `env_file: .env` (opcional);
  - `depends_on: db (healthy)`.

  El comando de `web` es `sh -c "alembic upgrade head && uvicorn ..."`, igual que el worker. Alembic no toma un lock por sí solo, así que `alembic/env.py` ejecuta `SELECT pg_advisory_xact_lock(4242)` antes de migrar. Si los dos servicios arrancan a la vez, uno espera al otro y luego no encuentra nada pendiente.
- **Desarrollo:** `npm run dev` en `frontend/` con proxy de `/api` a `localhost:8000`.

## Pruebas

**Backend** (pytest, Postgres con testcontainers, sin red):

| Área | Qué se prueba |
| --- | --- |
| top | Orden, excluye `no_aplica`, expiradas y las etiquetadas `mala`; incluye la etiqueta y si tiene postulación |
| jobs | Cada filtro solo y combinado, búsqueda sin distinguir tildes ni mayúsculas, paginación, `solo_cr`, 404 |
| feedback | Upsert `buena`/`mala`, `null` borra, 404 para oferta inexistente |
| profile | `PUT` válido crea versión; inválido → 422 con `loc` y sin escribir; `versions` ordenado; `from-cv` con `FakeLLMProvider` devuelve borrador y `texto_enviado` sin `@` y no crea versión; sin key → 503; archivo no PDF o mayor a 5 MB → 422 |
| applications | Crear, 409 duplicado, `PATCH` de estado actualiza `estado_desde` y llena `fecha_aplicacion`, `DELETE`, `seguimiento` a los 10 días y respeto de `recordatorio_hasta` |
| insights | `brechas_semana` agrupa sin distinguir mayúsculas e ignora las de más de 7 días; `skills` marca `tengo` y `brecha` y asigna el área; `daily` agrupa por día de Costa Rica; `flow` agrupa por tipo de fuente y semana |
| skill_areas | Asignaciones conocidas y caída a `otros` |
| ejemplos | Con menos de 6 etiquetas no hay sección; con suficientes, el prompt contiene `<preferencias_del_usuario>` con como máximo 4 y 4, sin datos personales y con los delimitadores limpios; `run_match` re-evalúa el top cuando cambia el hash (máximo 10) y no lo hace si el hash es igual |
| demo | `seed` es determinista (dos corridas → mismos conteos y mismos títulos), cubre todos los estados de postulación y las 12 semanas; en `DEMO_MODE`, `from-cv` → 503 y `insights` trae `demo: true` |
| app | Rutas no-API devuelven `index.html`; `/api/xyz` inexistente → 404 JSON |

**Frontend** (Vitest, Testing Library y MSW):
- Filtros de Explorar ↔ URL.
- Feedback optimista y deshacer.
- Kanban: mover por teclado llama al `PATCH` y revierte si falla.
- Formulario de perfil: errores 422 en el campo correcto; subir CV llena el formulario sin guardar.
- Modo reducido de movimiento: no se monta el canvas animado.
- Funciones puras del arte (sello determinista para el mismo nombre, cielo determinista para la misma fecha, huella normalizada) y contraste AA de los tokens.

**CI:** el job de Node corre `npm ci`, `npm test`, `npx tsc --noEmit` y `npm run build`.

**Verificación manual:** abrir `http://localhost:8000` en el navegador integrado y recorrer las 4 vistas con los datos reales, en claro y oscuro, a 360 px de ancho y con movimiento reducido. Lo mismo con `DEMO_MODE`.

## Seguridad y privacidad

- `web` solo escucha en `127.0.0.1`.
- `from-cv` redacta el CV antes de enviarlo (igual que la CLI) y devuelve el texto enviado para que el usuario lo vea.
- La descripción HTML de las ofertas nunca se inserta como HTML: el API la convierte a texto y el frontend la muestra como texto. Así se evita XSS desde el contenido externo.
- `DEMO_MODE` no toca `private/` ni llama al LLM.
- Los ejemplos de preferencias solo incluyen datos de ofertas públicas.

## Fuera de alcance

Correo diario, login y acceso desde otros dispositivos, notificaciones push, plan de estudio generado a partir de las brechas, dedupe aproximado, requisitos de la práctica UCR.
