# Fase 3: dashboard. Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** dashboard local (FastAPI + React) con 4 vistas, identidad "cielo nocturno", decoración, 7 piezas de arte con datos, recordatorios de seguimiento, `DEMO_MODE` y etiquetas usadas como ejemplos para Gemini.

**Architecture:** el paquete `moneyplease.api` (FastAPI) reutiliza los módulos existentes y sirve `/api/*` más el frontend compilado. El frontend vive en `frontend/` (Vite + React 19 + TS). Un servicio `web` nuevo en Compose, solo en `127.0.0.1:8000`. El código de agregación va en `moneyplease/insights.py`; el arte va en `frontend/src/art/`, con la lógica separada en funciones puras testeables.

**Tech Stack:** FastAPI, uvicorn, python-multipart; React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query, React Router, @dnd-kit/core, framer-motion, d3, simplex-noise; Vitest, @testing-library/react, MSW, jsdom.

**Spec:** `docs/superpowers/specs/2026-10-30-fase3-dashboard-design.md`

## Global Constraints

- **Backend:** `uv run pytest` desde `backend/`, sin red. **Frontend:** `npm test` y `npx tsc --noEmit` desde `frontend/`.
- **Commits** sin `Co-Authored-By`, en la rama `fase3`.
- **Red:** `web` escucha solo en `127.0.0.1:8000`. Sin login.
- **Contenido externo:** la descripción de las ofertas nunca se inserta como HTML (prohibido `dangerouslySetInnerHTML`).
- **Movimiento:** todo lo animado respeta `prefers-reduced-motion`. El arte usa `pointer-events: none` y va detrás del contenido.
- **Tokens** con los valores exactos del spec (tabla "Identidad visual"). Tipografías: Fraunces (títulos) e Inter (resto).
- **`DEMO_MODE`:** nunca toca `private/` ni llama al LLM.
- **Constantes:**
  - `FOLLOWUP_DAYS = 10` (configurable);
  - snooze de 7 días;
  - página de 25 en Explorar;
  - top de 10;
  - ejemplos: mínimo 6 etiquetas (al menos 2 buenas y 2 malas), máximo 4 + 4, ajuste de ±15 puntos, hasta 10 re-evaluaciones por corrida;
  - upload de CV: máximo 5 MB, `application/pdf`.

## Review Focus

1. **Perfil activo inexistente** (usuario nuevo o base vacía): todos los endpoints responden sin 500 (`/api/top` → `[]`, `/api/profile` → 404, insights vacíos) y el frontend muestra el estado vacío. Tests en las Tasks 3, 5, 7 y 11.
2. **Feedback o postulación sobre una oferta expirada o que desaparece:** 404 claro, y el frontend revierte la mutación optimista. Tests en las Tasks 3, 6 y 11.
3. **Búsqueda con caracteres especiales** (`%`, `_`, `'`, tildes, texto vacío): no rompe el SQL ni coincide con todo. Test en la Task 4.
4. **Arte con 0 o 1 dato** (sin skills, un solo día, una sola versión de perfil, sin postulaciones): las funciones puras no dividen por cero y los componentes se renderizan vacíos sin lanzar error. Tests en las Tasks 12–15.
5. **Dos pestañas o doble clic** en "Guardar" o "Guardar versión": la postulación duplicada → 409, manejado sin error visible. Las versiones del perfil no colisionan (`version` único → reintento). Tests en las Tasks 5 y 6.

---

## Estructura de archivos

```
backend/moneyplease/
  api/__init__.py app.py deps.py schemas.py
  api/routes/__init__.py top.py jobs.py profile.py applications.py insights.py
  insights.py skill_areas.py demo.py
  matching/examples.py                       (selección de ejemplos y hash)
backend/alembic/versions/0004_dashboard.py
backend/tests/api/conftest.py test_top.py test_jobs.py test_profile_api.py test_applications.py test_insights_api.py test_app.py
backend/tests/test_insights.py test_skill_areas.py test_examples.py test_demo.py
frontend/  package.json vite.config.ts tsconfig.json index.html
  src/main.tsx App.tsx theme.css
  src/api/client.ts types.ts hooks.ts
  src/components/ Layout.tsx JobCard.tsx ScoreRing.tsx CompanySeal.tsx StatusStrip.tsx Toast.tsx Kanban.tsx ApplicationEditor.tsx ProfileForm.tsx Filters.tsx JobDetail.tsx
  src/views/ Home.tsx Explore.tsx Applications.tsx Profile.tsx
  src/art/ seal.ts sky.ts glyph.ts constellation.ts garden.ts (lógica pura) + Constellation.tsx DailySky.tsx OfferRiver.tsx ProfileGlyph.tsx Garden.tsx FlowField.tsx Starfall.tsx
  src/decor/ NightGradient.tsx Grain.tsx EmptyState.tsx
  src/lib/ motion.ts contrast.ts
  src/test/ setup.ts handlers.ts
  src/**/*.test.ts(x)
```

---

### Task 1: Migración 0004, lock de migraciones y configuración

**Files:**
- Create: `backend/alembic/versions/0004_dashboard.py`
- Modify: `backend/alembic/env.py`, `backend/moneyplease/config.py`, `backend/moneyplease/db/models.py`, `backend/tests/conftest.py` (TRUNCATE de `applications`), `.env.example`
- Test: `backend/tests/test_migrations_0004.py`

**Interfaces:**
- Produces:
  - `Application` (`applications`), con las columnas exactas del spec. `job_id` es único y `notas` y `siguiente_paso` tienen default `""`.
  - `Match.ejemplos_hash: str | None`.
  - Nuevos campos de `Settings`: `followup_days: int = 10`, `demo_mode: bool = False`, `demo_database_url: str = "postgresql+psycopg://moneyplease:moneyplease@localhost:5432/moneyplease_demo"`.
  - La migración `0004` ejecuta `CREATE EXTENSION IF NOT EXISTS unaccent`.
  - `env.py` ejecuta `SELECT pg_advisory_xact_lock(4242)` dentro de la transacción de migración.

- [ ] **Step 1: Tests:**
  - `test_applications_table`: existen la tabla y la columna `matches.ejemplos_hash`.
  - `test_application_job_unique`: dos filas con el mismo `job_id` → `IntegrityError`.
  - `test_unaccent_available`: `SELECT unaccent('José')` devuelve `'Jose'`.
- [ ] **Step 2:** `uv run pytest tests/test_migrations_0004.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `uv run pytest -q`. Expected: todo PASS.
- [ ] **Step 5: Commit** `feat(db): migración 0004 con postulaciones, ejemplos_hash y unaccent`

---

### Task 2: Áreas de skills y agregaciones

**Files:**
- Create: `backend/moneyplease/skill_areas.py`, `backend/moneyplease/insights.py`
- Test: `backend/tests/test_skill_areas.py`, `backend/tests/test_insights.py`

**Interfaces:**
- Produces:
  - `skill_areas.AREAS = ("backend", "frontend", "datos", "cloud", "testing", "idiomas")`.
  - `skill_areas.area_of(skill: str) -> str`: compara la forma canónica contra un diccionario `SKILL_AREA`, con al menos 60 entradas comunes (java, spring boot, python, .net, node, rest, react, typescript, tailwind, angular, sql, mysql, postgresql, snowflake, power bi, etl, docker, kubernetes, aws, azure, gcp, ci/cd, junit, mockito, pytest, selenium, inglés/english…). Si no está, devuelve `"otros"`.
  - `skill_areas.find_skill(text: str) -> str | None`: la skill más larga del diccionario que aparece como palabra completa en el texto canónico.
  - `insights.gaps_week(session, profile_id, now, top=8) -> list[tuple[str, int]]`: cuenta las brechas de los matches con `evaluado_en ≥ now − 7 días`. Clave = `find_skill(frase)`; si no hay, `canonical(frase)`. Muestra la etiqueta original más frecuente de cada clave.
  - `insights.skills(session, profile: Profile, profile_id, limit=60) -> list[dict]`: `{skill, area, frecuencia, tengo, brecha}`. Fuentes: `find_skill` sobre fortalezas y brechas de todos los matches del perfil, más las skills del perfil (frecuencia mínima 1). `tengo` = la skill canónica está en el perfil.
  - `insights.daily(session, profile_id, now, dias=30) -> list[dict]`: `{fecha (ISO), nuevas, score_promedio | None}`. Nuevas = jobs con `primera_vez_visto` en ese día de `America/Costa_Rica`; el promedio sale de los matches de esas ofertas. Incluye los días con 0.
  - `insights.flow(session, now, semanas=12) -> list[dict]`: `{semana (lunes ISO), fuente (prefijo de source.key), nuevas}`. Incluye las combinaciones con 0.

- [ ] **Step 1: Tests:**
  - `area_of("Spring Boot") == "backend"`, `area_of("React 19") == "frontend"` (el mapeo usa `find_skill`), `area_of("Kubernetes") == "cloud"` y `area_of("Cobol") == "otros"`.
  - `find_skill("Pide experiencia con Kubernetes y AWS")` devuelve `"kubernetes"` o `"aws"` (la más larga) y no lanza error con `""`.
  - `gaps_week`: "Pide Kubernetes" y "kubernetes avanzado" cuentan como 2 para kubernetes; una brecha de hace 8 días se ignora; sin matches → `[]`.
  - `skills`: `tengo` y `brecha` correctos; skill del perfil sin aparecer en matches → frecuencia 1 y `tengo=True`.
  - `daily`: devuelve 30 días seguidos, el conteo cae en el día de Costa Rica (un job a las 01:00 UTC se cuenta el día anterior) y el promedio es `None` sin matches.
  - `flow`: devuelve 12 semanas × fuentes presentes, con `workday:hpe` y `workday:abbott` sumados en `workday`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5: Commit** `feat: áreas de skills y agregaciones para el dashboard`

---

### Task 3: App FastAPI, top y feedback

**Files:**
- Create: `backend/moneyplease/api/__init__.py`, `api/app.py`, `api/deps.py`, `api/schemas.py`, `api/routes/__init__.py`, `api/routes/top.py`, `api/routes/jobs.py` (solo feedback en esta tarea), `backend/tests/api/conftest.py`, `backend/tests/api/test_top.py`, `backend/tests/api/test_app.py`
- Modify: `backend/pyproject.toml` (`uv add fastapi uvicorn python-multipart`)

**Interfaces:**
- Produces:
  - `app.create_app(settings: Settings | None = None, session_factory=None, static_dir: Path | None = None) -> FastAPI`. Monta los routers bajo `/api`. Si `static_dir/index.html` existe, sirve `/assets` y un fallback SPA: cualquier GET que no empiece con `/api` devuelve `index.html`. `/api/<inexistente>` → 404 JSON.
  - `app.app = create_app()`. Usa `static_dir = Path("/app/static")` si existe.
  - `deps.get_session()`: un `Session` por request desde `app.state.session_factory`. `deps.get_settings()` lee `app.state.settings`. En demo, la sesión usa `demo_database_url`.
  - `schemas.JobOut {id, titulo, empresa, ubicacion, modalidad, url, fuente, publicado_en, pais}`, `MatchOut {score, fit, fortalezas, brechas, resumen}`, `TopItem {job: JobOut, match: MatchOut, etiqueta: str | None, postulacion_id: int | None}`.
  - `GET /api/top?n=10 -> list[TopItem]`.
  - `POST /api/jobs/{id}/feedback {valor}` → 204. Si la oferta no existe → 404.
  - `tests/api/conftest.py`: fixture `client` que crea `TestClient(create_app(settings, session_factory))` con el `session_factory` de los tests, más helpers `make_job(...)` y `make_match(...)`.

- [ ] **Step 1: Tests:**
  - `test_top_order_and_exclusions`: excluye `no_aplica`, expiradas y marcadas como mala; ordena por score.
  - `test_top_without_profile_empty` (Review Focus 1).
  - `test_top_includes_label_and_application`.
  - `test_feedback_upsert_and_clear`.
  - `test_feedback_unknown_job_404` (Review Focus 2).
  - `test_spa_fallback`: con un `index.html` temporal, `/postulaciones` → 200 HTML.
  - `test_unknown_api_404_json`.
- [ ] **Step 2:** Run. Expected: FAIL. **Step 3:** Implementar. **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat(api): app FastAPI con top, feedback y fallback SPA`

---

### Task 4: Explorar y detalle

**Files:**
- Modify: `backend/moneyplease/api/routes/jobs.py`, `api/schemas.py`
- Test: `backend/tests/api/test_jobs.py`

**Interfaces:**
- Produces:
  - `GET /api/jobs?q&source&modalidad&solo_cr&min_score&fit&desde&page=1&sort=score|fecha` → `{items: list[ExploreItem], total, page}`. `ExploreItem` es `{job, match | None, etiqueta}`.
    - `q`: se escapan `%`, `_` y `\`, y se filtra con `unaccent(lower(campo)) LIKE '%' || unaccent(lower(:q)) || '%' ESCAPE '\'` sobre título, empresa y descripción. Un `q` vacío o solo espacios se ignora.
    - Los filtros de score y fit usan el match del perfil activo (`LEFT JOIN`).
  - `GET /api/jobs/{id}` → `{job, descripcion_texto, match | None, etiqueta, postulacion}`. `descripcion_texto = normalize.html_to_text(descripcion)`.

- [ ] **Step 1: Tests:**
  - un test por filtro;
  - `test_search_accents_case` ("josé" encuentra "José");
  - `test_search_special_chars` (Review Focus 3): `q="%"` no devuelve todo; `q="_"` y `q="O'Reilly"` no lanzan error; `q="  "` = sin filtro;
  - `test_pagination_25`;
  - `test_detail_text_not_html` (la descripción `<p>a</p><script>x</script>` → sin `<`);
  - `test_detail_404`.
- [ ] **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5: Commit** `feat(api): explorar con filtros y detalle de oferta`

---

### Task 5: Perfil por API

**Files:**
- Create: `backend/moneyplease/api/routes/profile.py`
- Test: `backend/tests/api/test_profile_api.py`

**Interfaces:**
- Consumes: `profile.store` (`save`, `active`), `Profile`, `extract.pdf_text`, `extract.redact`, `generate.draft_from_text`, `matching.factory.build_llm` y `build_embedder` (vía `deps`, para poder sustituirlos en tests con `app.dependency_overrides`).
- Produces:
  - `GET /api/profile` → `{version, creado_en, perfil}` o 404.
  - `PUT /api/profile` (body = `Profile`) → 201 con la versión nueva. Si `store.save` choca por `version` única (`IntegrityError`), se reintenta una vez (Review Focus 5).
  - `GET /api/profile/versions` → `[{version, creado_en, perfil, areas}]`. `areas` es un dict con las 6 áreas de `skill_areas.AREAS`, cada una con la suma de niveles de sus skills (basico=1, intermedio=2, avanzado=3, asignadas con `area_of`); lo que cae en `otros` no se cuenta. Lo usa la Huella del perfil.
  - `POST /api/profile/from-cv` (`UploadFile`), con este orden de verificación:
    1. `DEMO_MODE` → 503 "Modo demo".
    2. Sin key → 503 "Falta GEMINI_API_KEY".
    3. `content_type != application/pdf` o tamaño > 5 MB → 422.
    4. Si pasa: guarda `private/cv.pdf`, extrae, redacta, escribe `private/cv.txt` y genera el borrador.
    5. `QuotaExceeded` → 429; `LLMError` o `httpx.HTTPError` → 502.
  - Respuesta de `from-cv`: `{perfil, texto_enviado}`.
  - `deps.get_llm()` y `deps.get_embedder()` son dependencias de FastAPI.

- [ ] **Step 1: Tests** (con `FakeLLMProvider` y `FakeEmbedder` vía overrides; `pdf_text` parcheado por monkeypatch):
  - `test_get_profile_404_then_ok`.
  - `test_put_valid_creates_version`.
  - `test_put_invalid_422_no_write`: `modalidad: ["remote"]` → `loc` contiene `preferences` y `modalidad`, y el número de versiones no cambia.
  - `test_put_twice_versions_increment`.
  - `test_versions_desc_with_areas`: orden descendente; un perfil con Spring Boot intermedio y Docker básico → `areas.backend == 2`, `areas.cloud == 1` y el resto 0.
  - `test_from_cv_returns_draft_not_saved` (`texto_enviado` sin `@` y sin nombre; versiones sin cambio).
  - `test_from_cv_no_key_503`.
  - `test_from_cv_not_pdf_422`.
  - `test_from_cv_too_big_422`.
  - `test_from_cv_quota_429`.
  - `test_from_cv_demo_503`.
- [ ] **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5: Commit** `feat(api): perfil (ver, guardar versión, historial y borrador desde CV)`

---

### Task 6: Postulaciones y seguimiento

**Files:**
- Create: `backend/moneyplease/api/routes/applications.py`
- Test: `backend/tests/api/test_applications.py`

**Interfaces:**
- Produces:
  - `applications.needs_followup(app: Application, now: datetime, days: int) -> bool` (función pura, la reutiliza `insights`).
  - `GET /api/applications` → `list[{id, estado, notas, fecha_aplicacion, siguiente_paso, estado_desde, recordatorio_hasta, seguimiento, dias_en_estado, job: JobOut, match: MatchOut | None}]`.
  - `POST /api/applications {job_id, estado="guardada"}` → 201. Si ya existe → 409. Si la oferta no existe → 404.
  - `PATCH /api/applications/{id}`: campos parciales. El estado se valida contra los 5 valores (422 si no). Si cambia el estado, `estado_desde = now`; si pasa a `aplicada` y `fecha_aplicacion` es nula, se llena con la fecha de hoy en Costa Rica.
  - `DELETE` → 204. Inexistente → 404.

- [ ] **Step 1: Tests:**
  - `test_create_and_duplicate_409` (Review Focus 5).
  - `test_create_unknown_job_404`.
  - `test_patch_state_updates_estado_desde_and_fecha`.
  - `test_patch_invalid_state_422`.
  - `test_followup_after_10_days`.
  - `test_followup_respects_snooze`.
  - `test_followup_only_aplicada`.
  - `test_delete`.
- [ ] **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5: Commit** `feat(api): postulaciones con recordatorios de seguimiento`

---

### Task 7: Insights por API

**Files:**
- Create: `backend/moneyplease/api/routes/insights.py`
- Test: `backend/tests/api/test_insights_api.py`

**Interfaces:**
- Consumes: `insights.*` (Task 2), `stats.collect`, `stats.match_status`, `eval.summary`, `needs_followup` (Task 6).
- Produces:
  - `GET /api/insights` → `{demo, brechas_semana: [{skill, n}], estado: {ultima_ingesta, fuentes_con_error: [key], matching: {fecha, candidatas, evaluadas, fallidas, cuota_agotada} | None, pendientes}, punto_control: {relevantes, etiquetadas}, seguimiento: [ApplicationOut]}`.
    - `ultima_ingesta` = máximo `IngestRun.terminado_en`.
    - `fuentes_con_error` = fuentes activas cuya última corrida tiene `ok=False`.
  - `GET /api/insights/skills`, `/daily?dias=30` y `/flow?semanas=12`: llaman a las funciones de la Task 2.
  - Sin perfil: `brechas_semana=[]`, `skills=[]`, `punto_control={relevantes: 0, etiquetadas: 0}` (Review Focus 1).

- [ ] **Step 1: Tests:**
  - `test_insights_shape_with_data`;
  - `test_insights_without_profile`;
  - `test_fuentes_con_error`;
  - `test_skills_daily_flow_endpoints`, que verifica el largo de `daily` (30) y de `flow` (12 × fuentes).
- [ ] **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5: Commit** `feat(api): insights para el dashboard y el arte`

---

### Task 8: Etiquetas como ejemplos para Gemini

**Files:**
- Create: `backend/moneyplease/matching/examples.py`
- Modify: `backend/moneyplease/matching/score.py`, `backend/moneyplease/matching/run.py`
- Test: `backend/tests/test_examples.py`; agregar a `tests/test_match_run.py`

**Interfaces:**
- Produces:
  - `examples.Ejemplo(titulo: str, empresa: str, resumen: str, le_intereso: bool)`.
  - `examples.select(session, profile_id) -> tuple[list[Ejemplo], str | None]`. Toma las etiquetas de ofertas con match en el perfil activo. Si hay menos de 6, o menos de 2 buenas o menos de 2 malas → `([], None)`. Si no, las 4 buenas y las 4 malas más recientes (`JobLabel.creado_en DESC`) y `hash = sha256(",".join(sorted(ids)))[:16]`. El `resumen` sale de `Match.resumen[:120]`.
  - `score.build_user_prompt(profile, job, ejemplos: list[Ejemplo] | None = None)`: si hay ejemplos, agrega `<preferencias_del_usuario>` después de `</perfil>`, con los textos pasados por `_clean`.
  - `score.SYSTEM_PROMPT` agrega la regla de ±15 del spec.
  - `score.evaluate(llm, profile, job, ejemplos=None)`.
  - `score.to_row(..., ejemplos_hash=None)`.
  - `run_match`:
    - obtiene los ejemplos una vez por corrida;
    - evalúa las ofertas nuevas con ellos;
    - después, con `insights_top = eval.top_matches(session, profile_id, 10)`, re-evalúa las del top cuyo `ejemplos_hash != hash_actual` y que no son ejemplo, hasta 10, haciendo upsert de `Match` (`session.merge`);
    - agrega el contador `MatchRun.reevaluadas`, que es un atributo en memoria impreso en el log (sin columna nueva).

- [ ] **Step 1: Tests:**
  - `test_select_needs_six_with_balance`: 5 etiquetas → vacío; 6 con 1 mala → vacío; 6 válidas → 4 + 2 y un hash estable.
  - `test_prompt_examples_section`: aparece la sección con máximo 4 + 4 y los delimitadores de los títulos se limpian.
  - `test_prompt_without_examples_unchanged`: idéntico al prompt actual.
  - En `test_match_run`:
    - `test_reevaluates_top_when_hash_changes`: tras etiquetar 6, la siguiente corrida re-evalúa ≤ 10 y guarda el hash nuevo.
    - `test_no_reevaluation_same_hash`.
    - `test_examples_not_reevaluated`.
- [ ] **Step 2–4:** FAIL → implementar → PASS (incluida la suite completa).
- [ ] **Step 5: Commit** `feat(matching): etiquetas como ejemplos de preferencia y re-evaluación del top`

---

### Task 9: DEMO_MODE y seed

**Files:**
- Create: `backend/moneyplease/demo.py`
- Modify: `backend/moneyplease/__main__.py` (subcomando `demo seed`), `api/deps.py` (base demo)
- Test: `backend/tests/test_demo.py`

**Interfaces:**
- Produces:
  - `demo.seed(session_factory, now: datetime, rng_seed: int = 42) -> dict[str, int]`: conteos por tabla.
    - Vacía todas las tablas y crea las 5 fuentes y las ~60 ofertas del spec (empresas ficticias, CR y remoto) con `primera_vez_visto` repartido en 12 semanas, embeddings deterministas (vector normalizado derivado del título con `random.Random`), un perfil con 2 versiones, matches con scores 20–95 y fits variados, 12 etiquetas (6 buenas y 6 malas) y 8 postulaciones (al menos una en cada estado, y una `aplicada` con `estado_desde = now − 14 días`).
  - `demo.ensure_database(url) -> None`: crea la base si no existe (conectándose a `postgres`) y corre `alembic upgrade head` con `-x url`.
  - CLI: `python -m moneyplease demo seed` usa `settings.demo_database_url`.

- [ ] **Step 1: Tests** (sobre la base de tests, llamando directo a `seed`):
  - `test_seed_deterministic`: dos corridas → mismos conteos y mismos títulos ordenados.
  - `test_seed_covers_states_and_weeks`: los 5 estados presentes, `primera_vez_visto` cubre 12 semanas distintas y hay ≥ 1 postulación con `needs_followup`.
  - `test_demo_api_flags`: con `create_app(Settings(demo_mode=True))`, `/api/insights` trae `demo: true` y `from-cv` → 503.
- [ ] **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5: Commit** `feat: DEMO_MODE con base aparte y datos ficticios deterministas`

---

### Task 10: Esqueleto del frontend, tokens y cliente API

**Files:**
- Create: `frontend/` (Vite React-TS), `src/theme.css`, `src/lib/contrast.ts`, `src/lib/motion.ts`, `src/api/{client,types,hooks}.ts`, `src/components/Layout.tsx`, `src/App.tsx`, `src/test/{setup,handlers}.ts`, `vite.config.ts` (proxy `/api` → `http://localhost:8000`; configuración de Vitest con jsdom)
- Test: `src/lib/contrast.test.ts`, `src/components/Layout.test.tsx`

**Interfaces:**
- Produces:
  - `theme.css`: las variables de la tabla del spec en `:root[data-theme=dark]` y `:root[data-theme=light]`, más Tailwind v4 (`@import "tailwindcss"` y `@theme` que mapea `--color-bg`, etc.). Fuentes Fraunces e Inter vía `<link>` en `index.html`.
  - `contrast.ratio(hex1, hex2) -> number` (WCAG). `TOKENS` se exporta desde `src/lib/tokens.ts` con los mismos valores que `theme.css`.
  - `motion.usePrefersReducedMotion(): boolean`.
  - `client.api.get<T>(path, params?)`, `post`, `put`, `patch` y `del`. Lanzan `ApiError {status, detail}`.
  - `types.ts`: los tipos de las respuestas de las Tasks 3–7.
  - `hooks.ts`: `useTop`, `useJobs(filters)`, `useJob(id)`, `useFeedback` (optimista sobre `["top"]` y `["jobs"]`, con revert en error), `useProfile`, `useProfileVersions`, `useSaveProfile`, `useDraftFromCv`, `useApplications`, `useCreateApplication`, `useUpdateApplication` (optimista), `useDeleteApplication`, `useInsights`, `useSkills`, `useDaily`, `useFlow`.
  - `Layout`: barra lateral con 4 enlaces (barra inferior por debajo de 768 px), toggle de tema (guardado en `localStorage`, por defecto según `prefers-color-scheme`, aplicado como `data-theme` en `<html>`) y banner "Modo demo" si `insights.demo`.

- [ ] **Step 1:** `npm create vite@latest frontend -- --template react-ts`; `npm i @tanstack/react-query react-router-dom @dnd-kit/core framer-motion d3 simplex-noise`; `npm i -D tailwindcss @tailwindcss/vite vitest jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom msw @types/d3`. Script `"test": "vitest run"`.
- [ ] **Step 2: Tests:**
  - `contrast`: `ratio("#000000", "#ffffff")` ≈ 21; **todos** los pares `text`/`bg`, `text`/`surface` y `muted`/`bg` de ambos temas dan ≥ 4.5.
  - `Layout`: renderiza los 4 enlaces; el toggle cambia `data-theme` y lo guarda; muestra el banner con `demo: true` (MSW).
- [ ] **Step 3:** `npm test`. Expected: FAIL. **Step 4:** Implementar. **Step 5:** `npm test && npx tsc --noEmit`. Expected: PASS.
- [ ] **Step 6: Commit** `feat(frontend): esqueleto con tokens cielo nocturno, layout y cliente API`

---

### Task 11: Inicio

**Files:**
- Create: `src/views/Home.tsx`, `src/components/{JobCard,ScoreRing,CompanySeal,StatusStrip,Toast}.tsx`, `src/art/seal.ts`
- Test: `src/views/Home.test.tsx`, `src/art/seal.test.ts`, `src/components/ScoreRing.test.tsx`

**Interfaces:**
- Produces:
  - `seal.sealParams(company: string): {sides: 3..8, rotation: 0..360, rings: 1..3, hue: 0..360}`: determinista, con el hash del string canónico (FNV-1a de 32 bits; no hace falta criptográfico en el navegador).
  - `CompanySeal({company, size=40})`: SVG.
  - `ScoreRing({score, fit})`: el arco es `score/100` de la circunferencia; `strokeDasharray` punteado si `fit === "practica"`; color `--danger` si < 50, mezcla si < 70, `--accent` si ≥ 70.
  - `JobCard({item, onFeedback, onSave})`.
  - `StatusStrip({insights})`.
  - `Toast`, con acción "Deshacer" durante 6 s.
  - `Home`: Cielo del día (placeholder hasta la Task 15), tira de estado, tarjetas (entrada escalonada con framer-motion, sin animar si hay movimiento reducido), tarjeta de brechas de la semana (lista; la mini-constelación entra en la Task 14), tarjeta de seguimiento (posponer y hecho) y estado vacío (placeholder hasta la Task 15).

- [ ] **Step 1: Tests:**
  - `seal`: mismo nombre → mismos parámetros; nombres distintos → al menos un parámetro distinto en 20 nombres; nombre vacío → no lanza error (Review Focus 4).
  - `ScoreRing`: score 0 y 100 renderizan; fit `practica` → hay `stroke-dasharray`.
  - `Home` (MSW):
    - muestra 2 tarjetas;
    - 👎 quita la tarjeta y "Deshacer" la devuelve y llama a feedback con `null`;
    - si feedback responde 404, la tarjeta vuelve y aparece un aviso (Review Focus 2);
    - "Guardar" llama a `POST /applications` y con un 409 no muestra error;
    - sin top → estado vacío con enlace a Perfil.
- [ ] **Step 2–4:** FAIL → implementar → PASS (`npm test && npx tsc --noEmit`).
- [ ] **Step 5: Commit** `feat(frontend): vista Inicio con tarjetas, anillo de score y sello de empresa`

---

### Task 12: Explorar y río de ofertas

**Files:**
- Create: `src/views/Explore.tsx`, `src/components/{Filters,JobDetail}.tsx`, `src/art/OfferRiver.tsx`, `src/art/river.ts`
- Test: `src/views/Explore.test.tsx`, `src/art/river.test.ts`

**Interfaces:**
- Produces:
  - `river.toSeries(flow: FlowPoint[]) -> {semanas: string[], fuentes: string[], matrix: number[][]}`: rellena con 0 las combinaciones que faltan.
  - `OfferRiver({flow})`: `d3.stack().offset(d3.stackOffsetWiggle)` con `d3.area().curve(d3.curveBasis)`; tooltip con el conteo. Con 0 o 1 semana se dibujan barras simples o "Sin datos todavía".
  - `Filters`: lee y escribe `useSearchParams` (`q` con debounce de 300 ms).
  - `JobDetail({id})`: la descripción va en `<p>` como texto, separada por saltos de línea, con los botones de interés, guardar y abrir.
  - `Explore`: río de ofertas, filtros, lista paginada y panel de detalle.

- [ ] **Step 1: Tests:**
  - `river`: rellena huecos; `[]` → matriz vacía sin error (Review Focus 4).
  - `Explore`: cambiar un filtro actualiza la URL y la request; abrir con `?modalidad=remoto&page=2` precarga los filtros; el detalle con `<script>` en el texto lo muestra literal (no ejecuta ni crea un elemento `script`).
- [ ] **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5: Commit** `feat(frontend): Explorar con filtros en la URL, detalle y río de ofertas`

---

### Task 13: Postulaciones, jardín y lluvia de estrellas

**Files:**
- Create: `src/views/Applications.tsx`, `src/components/{Kanban,ApplicationEditor}.tsx`, `src/art/{garden.ts,Garden.tsx,Starfall.tsx}`
- Test: `src/views/Applications.test.tsx`, `src/art/garden.test.ts`

**Interfaces:**
- Produces:
  - `garden.plantLayout(apps: {id: number, estado: string}[], width: number, height: number) -> {id, x, y, stage}[]`: posiciones deterministas por id (pseudoaleatorio con semilla = id), sin solaparse en una grilla con jitter. `stage` va de 0 a 4 según el estado; `rechazada` → `"wilted"`.
  - `Garden({apps, onSelect})`: SVG con formas por etapa; la flor usa el `hue` del sello de la empresa.
  - `Kanban({apps, onMove})`: `@dnd-kit` con `KeyboardSensor`.
  - `ApplicationEditor`.
  - `Starfall`: canvas con unas 40 estrellas durante 1,5 s, `pointer-events: none`. No se monta con movimiento reducido.
  - `Applications`: selector Jardín/Tablero (Jardín por defecto) y editor. Al pasar a `entrevista` u `oferta` se dispara `Starfall`.

- [ ] **Step 1: Tests:**
  - `garden`: determinista, mismas posiciones para los mismos ids; `[]` → `[]`; un solo elemento → dentro de los límites.
  - `Applications`:
    - mover con el teclado de Guardada a Aplicada llama a `PATCH` y la tarjeta cambia de columna;
    - si `PATCH` responde 500, revierte;
    - pasar a Entrevista monta el canvas de `Starfall`, salvo con movimiento reducido (mock de `matchMedia`);
    - el editor guarda las notas.
- [ ] **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5: Commit** `feat(frontend): postulaciones con jardín, tablero kanban y lluvia de estrellas`

---

### Task 14: Perfil, huella y constelación

**Files:**
- Create: `src/views/Profile.tsx`, `src/components/ProfileForm.tsx`, `src/art/{glyph.ts,ProfileGlyph.tsx,constellation.ts,Constellation.tsx}`
- Modify: `src/views/Home.tsx` (mini-constelación en la tarjeta de brechas)
- Test: `src/views/Profile.test.tsx`, `src/art/glyph.test.ts`, `src/art/constellation.test.ts`

**Interfaces:**
- Produces:
  - `glyph.normalize(versions: {areas: Record<Area, number>}[]) -> number[][]`: los ejes vienen calculados por el backend (`areas` de `/api/profile/versions`, Task 5), en el orden de `AREAS`. Divide por el máximo global y, si todo es 0, devuelve 0 sin dividir.
  - `ProfileGlyph({versions})`.
  - `constellation.layout(skills, width, height) -> {skill, x, y, r, opacity, color}[]`: un sector por área, radio ∝ √frecuencia y jitter determinista por hash.
  - `Constellation({skills, compact?})`.
  - `ProfileForm({value, onChange, errors})`: los `errors` vienen de los `loc` del 422 y se muestran junto a cada campo.
  - `Profile`:
    - el botón "Subir CV" (input file PDF) llama a `useDraftFromCv`, carga el borrador en el formulario sin guardar y muestra "Texto enviado a Gemini" plegable;
    - "Guardar versión";
    - historial con "Ver" y "Restaurar como nueva versión" (hace `PUT` con esa versión);
    - huella y constelación;
    - si `from-cv` responde 503, 429 o 502, muestra el mensaje del servidor.

- [ ] **Step 1: Tests:**
  - `glyph`: versión con todas las áreas en 0 → ejes en 0, sin `NaN` (Review Focus 4); `normalize` con una sola versión.
  - `constellation`: `[]` → `[]`; determinista.
  - `Profile` (MSW):
    - editar una skill y guardar envía el `PUT` correcto;
    - un 422 con `loc` de `preferences.modalidad` muestra el error junto a modalidad;
    - subir un PDF llena el formulario sin llamar a `PUT`;
    - un 503 muestra "Falta GEMINI_API_KEY";
    - "Restaurar" envía el `PUT` con la versión elegida;
    - doble clic en "Guardar versión" envía un solo `PUT` (botón deshabilitado mientras está pendiente; Review Focus 5).
- [ ] **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5: Commit** `feat(frontend): perfil editable con historial, huella y constelación de habilidades`

---

### Task 15: Decoración y cielo del día

**Files:**
- Create: `src/decor/{NightGradient,Grain,EmptyState}.tsx`, `src/art/{sky.ts,DailySky.tsx,FlowField.tsx}`
- Modify: `Layout.tsx` (fondo), `Home.tsx` (cielo y estado vacío), `Profile.tsx` (flow field), `Applications.tsx` y `Explore.tsx` (estados vacíos)
- Test: `src/art/sky.test.ts`, `src/decor/decor.test.tsx`

**Interfaces:**
- Produces:
  - `sky.skyParams(fecha: string, nuevas: number, scorePromedio: number | null) -> {stars: {x, y, r, a}[], top: string, bottom: string}`: generador con semilla de la fecha (mulberry32 sobre FNV-1a). Cantidad de estrellas `min(300, 40 + 4*nuevas)`. El color se interpola de `#1c2a5a` a `#5a2a3a` con `t = clamp((score − 40) / 50)`; si el score es `null`, `t = 0`.
  - `DailySky({daily})`: canvas, usa el último día.
  - `FlowField`: canvas, unas 600 partículas sobre `simplex-noise` 2D, 30 fps como tope. Se pausa con `document.hidden` y dibuja un solo fotograma con movimiento reducido.
  - `NightGradient`: dos `radial-gradient` animados con CSS (`@keyframes` de 60 s, desactivados en `@media (prefers-reduced-motion)`).
  - `Grain`: SVG `feTurbulence` con opacidad 0,04.
  - `EmptyState({kind: "sin-ofertas" | "sin-postulaciones" | "sin-perfil", action?})`: 3 SVG en línea con colores de los tokens.
  - El canvas y D3 se cargan con `React.lazy` y `Suspense`.

- [ ] **Step 1: Tests:**
  - `sky`: misma fecha → mismas estrellas; tope de 300; `score` nulo → color frío; 0 nuevas → 40 estrellas.
  - `decor`: `EmptyState` renderiza los 3 tipos con texto; con movimiento reducido, `FlowField` no llama a `requestAnimationFrame` más de una vez (mock); `NightGradient` y `Grain` tienen `aria-hidden` y `pointer-events: none`.
- [ ] **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5: Commit** `feat(frontend): decoración nocturna, flow field, estados vacíos y cielo del día`

---

### Task 16: Docker, CI y verificación en el navegador

**Files:**
- Modify: `backend/Dockerfile` (multi-etapa con contexto en la raíz), `docker-compose.yml` (servicio `web`; `worker.build` con `context: .` y `dockerfile: backend/Dockerfile`), `.dockerignore` en la raíz (`frontend/node_modules`, `backend/.venv`, `backend/private`, `backend/secrets`, `.git`), `.github/workflows/ci.yml` (job `frontend`), `README.md`

**Interfaces:**
- Consumes: todo lo anterior.

- [ ] **Step 1: Dockerfile.**
  - Etapa `frontend`: `FROM node:22-slim AS frontend`, `WORKDIR /app/frontend`, `COPY frontend/package*.json ./`, `RUN npm ci`, `COPY frontend/ ./`, `RUN npm run build`.
  - Etapa final: igual a la actual (con las rutas `backend/…` desde el contexto en la raíz), más `COPY --from=frontend /app/frontend/dist /app/static`.
- [ ] **Step 2: Compose.** Servicio `web`: `build` igual al del worker, `command: sh -c "alembic upgrade head && uvicorn moneyplease.api.app:app --host 0.0.0.0 --port 8000"`, `ports: ["127.0.0.1:8000:8000"]`, `env_file` opcional, `DATABASE_URL` como el worker, volúmenes `./backend/private:/app/private` y `hf_cache`, `depends_on: db healthy`, `restart: unless-stopped`.
- [ ] **Step 3: CI.** Job `frontend`: `actions/setup-node@v4` (Node 22) y `npm ci`, `npm test`, `npx tsc --noEmit`, `npm run build` en `frontend/`.
- [ ] **Step 4:** `docker compose up -d --build`. Expected: `db`, `worker` y `web` en estado running; `curl -s localhost:8000/api/insights` devuelve JSON; `curl -s localhost:8000/` devuelve HTML con `<div id="root">`. Comprobar que el puerto está ligado solo a `127.0.0.1` con `docker compose ps`.
- [ ] **Step 5: Navegador** (navegador integrado) en `http://localhost:8000`. Recorrer Inicio, Explorar, Postulaciones y Perfil con los datos reales:
  - marcar una oferta con 👍 y otra con 👎, deshacer y guardar una en el kanban;
  - mover la tarjeta a Aplicada;
  - abrir el detalle de una oferta;
  - editar una preferencia y guardar una versión;
  - todo en claro y oscuro, a 360 px y con movimiento reducido.

  Revisar la consola sin errores. Tomar capturas de las 4 vistas.
- [ ] **Step 6: Demo.** `docker compose exec web python -m moneyplease demo seed` y luego `DEMO_MODE=true docker compose up -d web`. Verificar el banner y las 7 piezas con datos. Volver a `DEMO_MODE` false.
- [ ] **Step 7:** README: sección "Dashboard" (URL, vistas, `DEMO_MODE`, desarrollo con `npm run dev`).
- [ ] **Step 8: Commit** `feat: servicio web en Docker, CI del frontend y README del dashboard`
- [ ] **Step 9:** No hacer push sin confirmación del usuario.
