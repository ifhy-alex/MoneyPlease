# Fase 4 — Rediseño "Medianoche y plata" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rehacer la capa visual del dashboard con la identidad "Medianoche y plata" y arte algorítmico (mapa semántico, grafo de habilidades, pipeline, flujo de señales, estallido), y cerrar los 12 defectos diferidos de la Fase 3.

**Architecture:** El backend agrega una proyección 2D pura (`projection.py`) y dos endpoints de solo lectura (`/api/map`, `/api/skills-graph`), además de arreglos puntuales en scoring, API e ingesta. El frontend cambia los tokens a un solo tema oscuro de vidrio y reemplaza cada pieza de arte por un par `*Layout.ts` (lógica pura y probada) + `*.tsx` (dibujo en canvas o SVG). Las vistas solo cambian qué piezas montan.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, pgvector, numpy · React 19, TypeScript, Vite, Tailwind v4, TanStack Query, d3 (d3-force, d3-shape), simplex-noise, Vitest + Testing Library + MSW 3.

**Spec:** `docs/superpowers/specs/2026-10-31-fase4-rediseno-design.md`

## Global Constraints

- **Rama:** `fase4-rediseno`. Los commits van en español con prefijo convencional (`feat:`, `fix:`, `test:`, `refactor:`, `docs:`) y **sin trailer `Co-Authored-By`**.
- **No leer** `backend/private/`, `backend/secrets/` ni `.env`.
- **Textos de la interfaz:** en español.
- **Un solo tema oscuro.** Tokens exactos: `--bg #04060F`, `--glass rgba(255,255,255,.045)`, `--glass-strong rgba(255,255,255,.07)`, `--line rgba(255,255,255,.09)`, `--line-strong rgba(255,255,255,.16)`, `--text #F1F5F9`, `--muted #7A8399`, `--silver #CBD5E1`, `--glow #2547B8`, `--ok #5FB89A`, `--danger #E0626F`.
- **Fuentes:** Geist (interfaz) y Geist Mono (puntajes, fechas, IDs, chips), empaquetadas con `@fontsource-variable/geist` y `@fontsource-variable/geist-mono`. No se usa Google Fonts ni Fraunces. Los números van con `tabular-nums`.
- **Nada con metáfora de naturaleza:** ni jardín, ni río, ni cielo, ni estrellas, ni constelación, ni luna, ni semilla. Eso aplica a nombres de archivo, `data-testid` y textos.
- **Movimiento reducido:** con `prefers-reduced-motion: reduce`, ninguna pieza anima. Se usa `usePrefersReducedMotion()` de `lib/motion.ts`.
- **Canvas:** DPR limitado a 2. Las animaciones de ambiente van a 30 fps como máximo y se pausan con `document.hidden`.
- **Determinismo:** las semillas salen de IDs o textos con `seeded()`/`mulberry32()` de `art/random.ts`. Nunca `Math.random` en lógica probada.
- **Sin scroll horizontal** a 360 px de ancho.
- **Comandos:**
  - backend: `cd backend && uv run pytest -q`;
  - frontend: `cd frontend && npx vitest run`, `npm run typecheck` y `npm run build`.
  - Postgres en `127.0.0.1`.

## Review Focus

1. **Perfil guardado sin ninguna oferta con embedding:** `/api/map` devuelve `{"total": 0, "puntos": []}` y Inicio muestra el `EmptyState` "sin-ofertas", sin romperse. Pruebas en la Tarea 5 y la Tarea 11.
2. **Habilidades con símbolos (`C#`, `.NET`, `C++`):** se detectan en el texto de la oferta, porque `\b` falla junto a `#`, `.` y `+`. Prueba en la Tarea 6 (`skills_in`).
3. **Celular / pantalla táctil:** en el mapa, el primer toque muestra el tooltip y el segundo abre el detalle. Prueba en la Tarea 11.
4. **Movimiento reducido en el mapa y el grafo:** no se programa ningún `requestAnimationFrame` después del primer dibujo. Pruebas en la Tarea 11 y la Tarea 12.
5. **Postulación rechazada en el pipeline:** va a la columna lateral, no rompe el orden de las demás y su nodo sigue siendo un botón editable. Prueba en la Tarea 13.

---

### Task 1: Recorte de la respuesta de Gemini y filtro de "ninguna brecha"

**Files:**
- Modify: `backend/moneyplease/matching/score.py:13-24` (`Item`, `MatchResult`)
- Test: `backend/tests/test_score.py`

**Interfaces:**
- Produces: `MatchResult` sigue con los mismos campos. Ahora **acepta** ítems largos y listas largas y los recorta; ya no lanza `string_too_long`.

- [ ] **Step 1: Write the failing tests**

```python
def test_match_result_recorta_items_largos_y_listas():
    r = MatchResult.model_validate({"score": 80, "fit": "junior",
        "fortalezas": ["x" * 200] + [f"f{i}" for i in range(7)],
        "brechas": ["Docker"], "resumen": "y" * 500})
    assert len(r.fortalezas) == 5
    assert r.fortalezas[0] == "x" * 119 + "…"
    assert len(r.resumen) == 300 and r.resumen.endswith("…")

@pytest.mark.parametrize("vacia", ["Ninguna brecha", "ninguna", "N/A", "Sin brechas", "NINGUNA BRECHA SIGNIFICATIVA", "ningúna"])
def test_brechas_vacias_se_descartan(vacia):
    r = MatchResult.model_validate({"score": 80, "fit": "junior", "fortalezas": [], "brechas": [vacia, "Kubernetes"], "resumen": "ok"})
    assert r.brechas == ["Kubernetes"]
```

- [ ] **Step 2: Run them and verify they fail**

Run: `cd backend && uv run pytest tests/test_score.py -q -k "recorta or vacias"`
Expected: FAIL. El primero con `string_too_long` / `too_long`; el segundo, con la brecha vacía todavía en la lista.

- [ ] **Step 3: Implement in `score.py`**

- `Item` usa `BeforeValidator(_clip(120))`.
- `fortalezas` y `brechas` usan `BeforeValidator(lambda v: list(v)[:5])`, y `resumen` usa `_clip(300)`.
- `_clip(n)` devuelve el texto tal cual si mide `n` caracteres o menos; si mide más, lo corta a `n-1` caracteres y agrega `"…"`.
- Las brechas vacías se filtran con un `AfterValidator` en `brechas`: se descartan los ítems cuyo texto canónico (minúsculas, sin acentos, con `unicodedata.normalize("NFKD")`) es `"n/a"`, `"na"`, `"ninguna"`, o empieza por `"ninguna brecha"` o `"sin brechas"`.

- [ ] **Step 4: Run the tests**

Run: `cd backend && uv run pytest tests/test_score.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/moneyplease/matching/score.py backend/tests/test_score.py
git commit -m "fix: recortar respuestas largas de Gemini y descartar 'ninguna brecha'"
```

---

### Task 2: Arreglos de la API (feedback concurrente, `n` de top, `cv_texto`, demo sin sembrar)

**Files:**
- Modify: `backend/moneyplease/api/routes/jobs.py:24-37` (`feedback`)
- Modify: `backend/moneyplease/api/routes/top.py:13-14`
- Modify: `backend/moneyplease/api/routes/profile.py:59-70` (`put_profile`)
- Modify: `backend/moneyplease/api/app.py` (`create_app`)
- Test: `backend/tests/api/test_jobs.py`, `test_top.py`, `test_profile_api.py`, `test_app.py`

**Interfaces:**
- Consumes: el fixture `World` de `tests/api/conftest.py`.
- Produces:
  - `GET /api/top?n=` acepta 1–50 y responde 422 fuera de ese rango.
  - En modo demo, un `ProgrammingError` se convierte en 503 con `{"detail": "Modo demo sin datos: corre `demo seed`"}`.

- [ ] **Step 1: Write the failing tests**

- `test_jobs.py::test_feedback_upsert_no_falla_si_la_etiqueta_aparece_entre_medias`:
  - Crea una oferta y llama a `feedback`, monkeypatcheando `session.get(JobLabel, …)` para que devuelva `None` aunque ya exista una fila, igual que en la carrera real.
  - Comprueba que la respuesta es 204 y que hay una sola fila con `etiqueta == "mala"`.
- `test_top.py::test_n_fuera_de_rango_es_422`: `client.get("/api/top?n=-1").status_code == 422` y lo mismo con `n=51`.
- `test_profile_api.py::test_put_usa_el_cv_txt_mas_reciente`:
  - Parte de un perfil activo con `cv_texto="viejo"` y escribe `settings.private_dir / "cv.txt"` con `"nuevo"`.
  - Hace PUT con el perfil y comprueba que la versión nueva tiene `cv_texto == "nuevo"`.
- `test_profile_api.py::test_put_ignora_cv_txt_anterior_a_la_version`: el mismo caso, pero con `os.utime(cv_txt, (0, 0))`; la versión nueva conserva `"viejo"`.
- `test_app.py::test_demo_sin_sembrar_responde_503`:
  - Crea la app con `Settings(demo_mode=True, …)` y un `session_factory` falso cuya sesión lanza `sqlalchemy.exc.ProgrammingError("SELECT", {}, Exception("relation \"jobs\" does not exist"))` en `execute` y en `scalars`.
  - `GET /api/top` responde 503 con el `detail` exacto.

- [ ] **Step 2: Run them and verify they fail**

Run: `cd backend && uv run pytest tests/api -q -k "upsert or rango or cv_txt or sembrar"`
Expected: 5 FAIL (IntegrityError / 500 / 200 / "viejo" / 500).

- [ ] **Step 3: Implement**

- **`feedback`:** con valor, usa `sqlalchemy.dialects.postgresql.insert(JobLabel).values(job_id=…, etiqueta=…).on_conflict_do_update(index_elements=[JobLabel.job_id], set_={"etiqueta": …})`. Con `None`, hace `delete(JobLabel).where(JobLabel.job_id == job_id)`.
- **`top`:** `n: int = Query(10, ge=1, le=50)`.
- **`put_profile`:** agrega `settings: Settings = Depends(get_settings)`. Calcula `cv_txt = settings.private_dir / "cv.txt"` y lo usa si existe y `datetime.fromtimestamp(cv_txt.stat().st_mtime, UTC) > activo.creado_en`. Si no hay versión activa pero el archivo existe, también lo usa. En cualquier otro caso usa el `cv_texto` de la versión activa, o `""`.
- **`create_app`:** si `settings.demo_mode`, registra `@app.exception_handler(ProgrammingError)` que devuelve `JSONResponse({"detail": "Modo demo sin datos: corre `demo seed`"}, 503)`.

- [ ] **Step 4: Run backend suite**

Run: `cd backend && uv run pytest -q`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/moneyplease/api backend/tests/api
git commit -m "fix(api): upsert de feedback, rango de n en top, cv_texto actual y 503 en demo sin datos"
```

---

### Task 3: Workday en mantenimiento

**Files:**
- Modify: `backend/moneyplease/ingest/base.py` (agregar excepción)
- Modify: `backend/moneyplease/ingest/connectors/workday.py:44-47` (`_jobs`) y el GET de detalle en `_job`
- Test: `backend/tests/test_workday.py`

**Interfaces:**
- Produces:
  - `class Maintenance(Exception)` en `ingest/base.py`.
  - El conector lanza `Maintenance("Workday en mantenimiento")`, y el resumen de ingesta muestra `error=Maintenance: Workday en mantenimiento` (`run.py` ya formatea `type: msg`).

- [ ] **Step 1: Write the failing tests**

```python
def test_redireccion_a_mantenimiento(respx_mock, connector):
    respx_mock.post(JOBS_URL).respond(303, headers={"Location": "https://community.workday.com/maintenance-page"})
    respx_mock.get("https://community.workday.com/maintenance-page").respond(200, html="<html>maintenance</html>")
    with pytest.raises(Maintenance, match="Workday en mantenimiento"):
        connector.fetch()

def test_respuesta_html_no_json_es_mantenimiento_si_la_url_lo_dice(respx_mock, connector): ...
```

`JOBS_URL` y `connector` son los fixtures que ya usa `test_workday.py`. Se agregan si no existen, con robots permitido.

- [ ] **Step 2: Run them and verify they fail**

Run: `cd backend && uv run pytest tests/test_workday.py -q -k mantenimiento`
Expected: FAIL (`HTTPStatusError` o `JSONDecodeError`).

- [ ] **Step 3: Implement**

- Agregar `_is_maintenance(resp: httpx.Response) -> bool` en `workday.py`: es verdadero si `"maintenance"` aparece en `str(resp.url)`, en `resp.headers.get("location", "")` o en la URL de alguna respuesta de `resp.history`.
- Envolver las llamadas en `_jobs` y en `_job`:
  - capturar `httpx.HTTPStatusError` y revisar `exc.response`;
  - también revisar la respuesta exitosa antes de llamar a `.json()`;
  - si es mantenimiento, lanzar `Maintenance("Workday en mantenimiento")`; si no, relanzar el error original.

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_workday.py tests/test_run.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/moneyplease/ingest backend/tests/test_workday.py
git commit -m "fix(workday): reportar 'Workday en mantenimiento' en vez de JSONDecodeError"
```

---

### Task 4: Proyección 2D

**Files:**
- Create: `backend/moneyplease/projection.py`
- Test: `backend/tests/test_projection.py`

**Interfaces:**
- Produces: `project(profile: np.ndarray, jobs: np.ndarray, ids: list[int]) -> list[tuple[float, float, float]]`.
  - Recibe vectores normalizados: `profile` de forma `(d,)` y `jobs` de forma `(n, d)`.
  - Devuelve `(x, y, similitud)` por fila, en el mismo orden.

- [ ] **Step 1: Write the failing tests**

- `test_radio_crece_con_la_distancia`: con 4 vectores sintéticos de similitudes 0.9, 0.7, 0.5 y 0.3, `hypot(x, y)` vale 0, ⅓, ⅔ y 1 (±1e-6).
- `test_similitud_constante_da_radio_medio`: todos con `hypot == 0.5`.
- `test_signo_determinista`: proyectar `jobs` y `-residuos` reflejados da los mismos `(x, y)`. Equivale a probar que el signo de cada componente se fija con su carga de mayor valor absoluto positiva. Se construye con una matriz fija y se compara contra la misma llamada con las filas en otro orden, mapeando por id.
- `test_menos_de_tres_reparte_por_id`: con 2 ofertas (ids 5 y 9), los ángulos son `2π·rank/n`, ordenando por id: el id 5 en 0 y el id 9 en π.
- `test_vacio`: `project(p, np.empty((0, d)), []) == []`.

- [ ] **Step 2: Run them and verify they fail**

Run: `cd backend && uv run pytest tests/test_projection.py -q`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement `project` siguiendo la spec §3.1**

```python
s = jobs @ profile
r = (s.max() - s) / (s.max() - s.min()) if s.max() > s.min() else np.full_like(s, 0.5)
if n < 3: theta = 2π·rank(id)/n
else:
    res = jobs - np.outer(s, profile)
    res -= res.mean(axis=0)
    _, _, vt = np.linalg.svd(res, full_matrices=False)
    comps = vt[:2]; comps *= np.sign(comps[np.arange(2), np.abs(comps).argmax(axis=1)])[:, None]
    c = res @ comps.T; theta = np.arctan2(c[:, 1], c[:, 0])
return [(r·cosθ, r·sinθ, s)]
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_projection.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/moneyplease/projection.py backend/tests/test_projection.py
git commit -m "feat: proyección 2D de ofertas alrededor del perfil"
```

---

### Task 5: `GET /api/map`

**Files:**
- Create: `backend/moneyplease/api/routes/map.py`
- Modify: `backend/moneyplease/api/app.py` (incluir router)
- Modify: `backend/moneyplease/api/schemas.py` (agregar `MapPoint`, `MapData`)
- Test: `backend/tests/api/test_map.py`

**Interfaces:**
- Consumes:
  - `project` de la Tarea 4;
  - `passes(job, prefs)` de `matching/filters.py`;
  - `store.active(session)`;
  - `Profile.model_validate(row.perfil_json).preferences`.
- Produces:
  - `MapPoint{job_id:int, titulo:str, empresa:str, x:float, y:float, similitud:float, puntaje:int|None, etiqueta:str|None}`;
  - `MapData{total:int, puntos:list[MapPoint]}`.

- [ ] **Step 1: Write the failing tests** (con `World` y embeddings de `FakeEmbedder`)

- `test_sin_perfil_404`: `GET /api/map` responde 404 con `detail == "Todavía no hay perfil guardado"`.
- `test_perfil_sin_ofertas_con_embedding`:
  - Ofertas creadas con `embedding=None`.
  - La respuesta es `{"total": 0, "puntos": []}`.
- `test_excluye_no_interesa_filtros_duros_y_sin_embedding`:
  - Hay una oferta con etiqueta `mala`, otra con título "Senior Engineer", otra sin embedding y dos válidas.
  - Solo las dos válidas aparecen.
  - Las válidas que tienen match traen `puntaje` y `etiqueta`.
- `test_maximo_300_las_mas_cercanas`:
  - Se crean 305 ofertas válidas con embeddings decrecientes en similitud.
  - Aparecen 300 puntos, el `total` es 300 y no está el id menos similar.
- `test_coordenadas_en_rango`: todas cumplen `-1 ≤ x, y ≤ 1` y `hypot ≤ 1 + 1e-9`.

- [ ] **Step 2: Run them and verify they fail**

Run: `cd backend && uv run pytest tests/api/test_map.py -q`
Expected: FAIL (404 de la ruta)

- [ ] **Step 3: Implement `get_map(session) -> MapData`**

- Query: `Job` activo con `embedding IS NOT NULL`, sin `JobLabel.etiqueta == "mala"`, ordenado por `Job.embedding.cosine_distance(perfil.embedding)` y limitado a 600.
- En Python, filtrar con `passes` y quedarse con las primeras 300.
- Hacer outerjoin con `Match` del perfil activo para tener `puntaje` (`Match.score`) y con `JobLabel` para la etiqueta.
- `project(np.array(perfil.embedding), np.array([j.embedding …]), ids)`.

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/api -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/moneyplease/api backend/tests/api/test_map.py
git commit -m "feat(api): /api/map con la proyección de ofertas"
```

---

### Task 6: `GET /api/skills-graph`

**Files:**
- Modify: `backend/moneyplease/skill_areas.py` (agregar `skills_in`)
- Create: `backend/moneyplease/api/routes/graph.py`
- Modify: `backend/moneyplease/api/app.py`, `backend/moneyplease/api/schemas.py`
- Test: `backend/tests/test_skill_areas.py`, `backend/tests/api/test_graph.py`

**Interfaces:**
- Consumes:
  - `top_matches(session, profile_id, 40, hide_rejected=True)` de `eval.py`;
  - `canonical`, `SKILL_AREA` y `area_of` de `skill_areas.py`.
- Produces:
  - `skills_in(text: str) -> set[str]`: todas las habilidades conocidas en forma canónica, como palabra completa, con los límites `(?<![\w#+.])` y `(?![\w#+])`.
  - Esquemas: `GraphSkill{nombre, nivel:str|None, area, grado:int, tiene:bool}`, `GraphOffer{job_id, titulo, empresa, puntaje:int}`, `GraphEdge{habilidad, job_id}` y `SkillsGraph{habilidades, ofertas, aristas}`.

- [ ] **Step 1: Write the failing tests**

- `test_skills_in_con_simbolos`: `skills_in("Buscamos C# y .NET, ideal C++ y Java")` contiene `{"c#", ".net", "c++", "java"}`. Si alguna no existe en `SKILL_AREA`, se agrega a `_BY_AREA["backend"]` en el mismo paso.
- `test_skills_in_no_confunde_java_con_javascript`: `skills_in("JavaScript dev") == {"javascript"}`.
- `test_graph_404_sin_perfil`.
- `test_graph_sin_matches_listas_vacias`: responde `{"habilidades": [], "ofertas": [], "aristas": []}`.
- `test_graph_aristas_y_faltantes`:
  - El perfil tiene `Java` y `Python`.
  - Hay 3 ofertas con match; sus descripciones mencionan Java, Docker y Kubernetes.
  - Las aristas de Java van a las ofertas correctas.
  - Docker y Kubernetes aparecen con `tiene=False`, y `grado` es el número de ofertas que las piden.
  - Python, sin ofertas, aparece con `grado == 0` y `tiene=True`.
- `test_graph_maximo_8_faltantes`: con 10 habilidades faltantes distintas solo aparecen las 8 de mayor grado.

- [ ] **Step 2: Run them and verify they fail**

Run: `cd backend && uv run pytest tests/test_skill_areas.py tests/api/test_graph.py -q`
Expected: FAIL

- [ ] **Step 3: Implement `skills_in` and `get_skills_graph(session) -> SkillsGraph`**

- Las habilidades del perfil se pasan por `canonical`.
- Por oferta: `skills_in(titulo + " " + descripcion)`.
- Hay arista si la habilidad está en el perfil o está entre las 8 faltantes de mayor grado (desempate por nombre).
- `nombre` usa el texto del perfil cuando `tiene=True`, y la forma canónica en mayúsculas iniciales cuando no.

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest -q`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/moneyplease backend/tests
git commit -m "feat(api): /api/skills-graph y detección de habilidades con símbolos"
```

---

### Task 7: Identidad visual — tokens, fuentes, solo modo oscuro, componentes de vidrio

**Files:**
- Modify: `frontend/src/theme.css`, `frontend/src/lib/tokens.ts`, `frontend/index.html`, `frontend/package.json`
- Modify: `frontend/src/main.tsx` (importar fuentes)
- Modify: `frontend/src/components/Layout.tsx` (quitar `useTheme` y el botón de tema)
- Modify (solo clases y estilos): `JobCard.tsx`, `ScoreRing.tsx`, `StatusStrip.tsx`, `Filters.tsx`, `Kanban.tsx`, `Toast.tsx`, `ProfileForm.tsx`, `CompanySeal.tsx`
- Test: `frontend/src/lib/contrast.test.ts`, `frontend/src/components/Layout.test.tsx`, `frontend/src/components/ScoreRing.test.tsx`

**Interfaces:**
- Produces:
  - `TOKENS` como **un solo objeto plano** con `{bg, glass, text, muted, silver, glow, ok, danger}`. Para `glass` se usa su color compuesto sobre `bg`, `#0E1019`, porque el test de contraste necesita un hex.
  - Desaparecen el tipo `Theme`, `useTheme` y `data-theme`.
  - Clases utilitarias en `theme.css`:
    - `.glass`: fondo `--glass`, borde `--line`, `backdrop-filter: blur(14px)`, radio 14px;
    - `.glass-hover`: el brillo radial con `--mx/--my`;
    - `.mono`: Geist Mono con `tabular-nums`.
  - `ScoreRing`: el arco es `--silver` cuando el puntaje es 60 o más y `--muted` cuando es menor. Ya no usa colores semáforo.

- [ ] **Step 1: Update the tests first**

- `contrast.test.ts`: un solo `it` que comprueba ratio ≥ 4.5 para `[text,bg]`, `[text,glass]`, `[muted,bg]`, `[muted,glass]`, `[silver,bg]` y `[silver,glass]`.
- `Layout.test.tsx`:
  - Se borra el test del selector de tema.
  - Se agrega `test('no hay selector de tema')`: `queryByRole('button', {name: /tema/i})` es null.
- `ScoreRing.test.tsx`: `scoreColor(85) === 'var(--silver)'` y `scoreColor(40) === 'var(--muted)'`.

- [ ] **Step 2: Run them and verify they fail**

Run: `cd frontend && npx vitest run src/lib src/components/Layout.test.tsx src/components/ScoreRing.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement**

- Instalar las fuentes con `npm i @fontsource-variable/geist @fontsource-variable/geist-mono`, importarlas en `main.tsx` y quitar los `<link>` de Google Fonts de `index.html`.
- `theme.css`:
  - define los tokens del Global Constraints en `:root`, una sola vez;
  - `body { background: var(--bg); color: var(--text); font-family: 'Geist Variable', system-ui }`;
  - mapea en `@theme` los colores de Tailwind ya usados (`bg-surface → --glass`, `border-line → --line`, `text-accent → --silver`) para que las clases existentes sigan resolviendo;
  - borra el bloque claro y los keyframes del gradiente nocturno.
- Componentes:
  - Las tarjetas y paneles pasan a `glass`.
  - Los puntajes, fechas y chips de habilidades pasan a `mono`.
  - Los títulos pasan de Fraunces a Geist 600, con tamaños 28/20/15/13.

- [ ] **Step 4: Run frontend checks**

Run: `cd frontend && npx vitest run && npm run typecheck`
Expected: PASS. Las vistas pueden seguir montando las piezas viejas; se reemplazan en tareas siguientes.

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat(frontend): identidad medianoche y plata, solo modo oscuro y fuentes Geist"
```

---

### Task 8: Ambiente — `AmbientField`, `Grain` y `EmptyState` algorítmico

**Files:**
- Create: `frontend/src/decor/AmbientField.tsx`
- Delete: `frontend/src/decor/NightGradient.tsx`, `frontend/src/art/FlowField.tsx`
- Modify: `frontend/src/decor/Grain.tsx` (opacidad 0.035), `frontend/src/decor/EmptyState.tsx`, `frontend/src/App.tsx`, `frontend/src/views/Profile.tsx` (quitar FlowField)
- Test: `frontend/src/decor/decor.test.tsx`

**Interfaces:**
- Produces:
  - `export default function AmbientField()`: un canvas `aria-hidden="true"` con clase `pointer-events-none fixed inset-0 -z-10`.
  - `EmptyState` mantiene su API `{kind, title, text, children}`. Su arte pasa a `PATTERNS: Record<EmptyKind, () => ReactNode>`: `'sin-ofertas'` usa una retícula de puntos, `'sin-postulaciones'` líneas de contorno y `'sin-perfil'` Truchet. Son SVG deterministas con semilla `kind`.

- [ ] **Step 1: Update tests**

En `decor.test.tsx`:
- reemplazar `NightGradient` y `FlowField` por `AmbientField` en los tres tests existentes;
- agregar `test('con la pestaña oculta no programa más cuadros')`: mockear `document.hidden = true`, disparar `visibilitychange` y comprobar que la cantidad de llamadas a `requestAnimationFrame` no sube después de avanzar timers.

- [ ] **Step 2: Run them and verify they fail**

Run: `cd frontend && npx vitest run src/decor`
Expected: FAIL (módulo inexistente)

- [ ] **Step 3: Implement**

`AmbientField`:
- unas 260 partículas sobre un campo de `createNoise3D` (simplex-noise), con semilla `seeded('ambient')`;
- color `--glow` al 18% y un 15% de las partículas en `--silver` al 12%;
- estelas con `fillRect` de `--bg` al 8% por cuadro, más un halo radial azul arriba que se dibuja una vez por cuadro;
- un cuadro cada ≥33 ms;
- con movimiento reducido, un solo cuadro y sin `requestAnimationFrame` después.

`App.tsx` monta `<AmbientField/><Grain/>`.

- [ ] **Step 4: Run tests**

Run: `cd frontend && npx vitest run && npm run typecheck`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A frontend/src
git commit -m "feat(frontend): fondo de campo de flujo y estados vacíos generativos"
```

---

### Task 9: Diálogos accesibles y confirmación de borrado

**Files:**
- Create: `frontend/src/components/Dialog.tsx`
- Modify: `frontend/src/components/JobDetail.tsx`, `frontend/src/components/ApplicationEditor.tsx`
- Test: `frontend/src/components/Dialog.test.tsx`, `frontend/src/views/Applications.test.tsx`

**Interfaces:**
- Produces:
  - `Dialog({ title, onClose, children, variant = 'center' }: { title: string; onClose: () => void; children: ReactNode; variant?: 'center' | 'side' })`:
    - renderiza `role="dialog"`, `aria-modal="true"` y `aria-labelledby`, sobre un fondo `--bg` al 60%;
    - Escape llama a `onClose`;
    - al abrir, el foco va al primer elemento enfocable;
    - Tab y Shift+Tab hacen ciclo dentro del diálogo;
    - al desmontar, el foco vuelve al elemento que lo tenía antes.
  - `ConfirmDialog({ title, text, confirmLabel, onConfirm, onCancel })`: es un `Dialog` con dos botones. El de confirmar usa el estilo destructivo (`--danger`).

- [ ] **Step 1: Write the failing tests**

- `Dialog.test.tsx`:
  - `cierra con Escape`;
  - `enfoca el primer botón al abrir`;
  - `Tab desde el último vuelve al primero`;
  - `devuelve el foco al cerrar`: se renderiza un botón disparador, se abre, se cierra y el disparador tiene el foco.
- `Applications.test.tsx`:
  - `borrar pide confirmación y cancelar no borra`: abrir el editor, clic en "Borrar" y aparece "¿Borrar esta postulación?"; con "Cancelar", el handler `DELETE` no se llamó.
  - `confirmar borra`: con "Borrar" en la confirmación, `DELETE /api/applications/1` se llama una vez.

- [ ] **Step 2: Run them and verify they fail**

Run: `cd frontend && npx vitest run src/components/Dialog.test.tsx src/views/Applications.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement**

- `JobDetail` usa `<Dialog variant="side" title={...}>`: el panel lateral derecho, con ancho máximo xl.
- `ApplicationEditor` usa `<Dialog>`, y su botón "Borrar" abre el `ConfirmDialog` antes de llamar a `onDelete`.

- [ ] **Step 4: Run tests**

Run: `cd frontend && npx vitest run && npm run typecheck`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "fix(frontend): diálogos accesibles y confirmación al borrar una postulación"
```

---

### Task 10: Hooks y datos nuevos, invalidación al guardar el perfil y feedback optimista en Explorar

**Files:**
- Modify: `frontend/src/api/types.ts`, `frontend/src/api/hooks.ts`, `frontend/src/test/handlers.ts`
- Modify: `frontend/src/components/JobCard.tsx` (`ActionButton` con `pressed`), `frontend/src/components/JobDetail.tsx`
- Test: `frontend/src/api/hooks.test.tsx` (nuevo), `frontend/src/views/Explore.test.tsx`

**Interfaces:**
- Consumes: las respuestas de las Tareas 5 y 6.
- Produces:
  - **Tipos** en `types.ts`:
    - `MapPoint`, `MapData`, `GraphSkill`, `GraphOffer`, `GraphEdge` y `SkillsGraph`, con los mismos nombres de campos que la API;
    - `etiqueta` es `Etiqueta | null` y `nivel` es `string | null`.
  - **Hooks:** `useMap()` (clave `['map']`, `retry: false`) y `useSkillsGraph()` (clave `['skills-graph']`, `retry: false`).
  - **`useSaveProfile`** invalida además `['top']`, `['insights']`, `['map']` y `['skills-graph']`.
  - **`useFeedback`:**
    - en `onMutate` también actualiza de forma optimista `['job', jobId]` (`etiqueta`) y todas las `['jobs', …]` mediante `setQueriesData`;
    - en `onError` revierte esos cambios;
    - en `onSettled` invalida además `['map']`.
  - **`ActionButton`** recibe `pressed?: boolean` y lo pone en `aria-pressed`. `JobDetail` pasa `pressed={d.etiqueta === 'buena'}` a "Me interesa" y `pressed={d.etiqueta === 'mala'}` a "No me interesa".
  - **`handlers.ts`:** por defecto, `GET /api/map` devuelve `{total:0,puntos:[]}` y `GET /api/skills-graph` devuelve listas vacías. Se agregan los helpers `mapPoint(id, puntaje)` y `skillsGraph()` para las pruebas.

- [ ] **Step 1: Write the failing tests**

- `hooks.test.tsx::guardar el perfil vuelve a pedir el top y el mapa`:
  - Se monta un componente que usa `useTop`, `useMap` y `useSaveProfile`, contando las llamadas a `GET /api/top` y `/api/map`.
  - Después de `mutate(perfil)` y el PUT 201, cada contador llega a 2.
- `Explore.test.tsx::el feedback del detalle es inmediato`:
  - El handler de `POST /api/jobs/7/feedback` hace `await delay('infinite')`.
  - Se abre el detalle de "Backend Intern" y se hace clic en "No me interesa".
  - El botón tiene `aria-pressed="true"` antes de que responda el servidor.

- [ ] **Step 2: Run them and verify they fail**

Run: `cd frontend && npx vitest run src/api src/views/Explore.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement** según el bloque Interfaces.

- [ ] **Step 4: Run tests**

Run: `cd frontend && npx vitest run && npm run typecheck`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): hooks del mapa y del grafo; perfil refresca Inicio; feedback optimista en Explorar"
```

---

### Task 11: Mapa semántico en Inicio

**Files:**
- Create: `frontend/src/art/mapLayout.ts`, `frontend/src/art/SemanticMap.tsx`
- Modify: `frontend/src/views/Home.tsx` (quitar `DailySky` y la constelación compacta; montar `SemanticMap` arriba)
- Test: `frontend/src/art/mapLayout.test.ts`, `frontend/src/views/Home.test.tsx`

**Interfaces:**
- Consumes: `useMap()` y `MapPoint` (Tarea 10); el `JobDetail` existente para abrir el detalle.
- Produces:
  - `type Tone = 'sin' | 'bajo' | 'alto'`.
  - `radiusFor(puntaje: number | null): number`: `null` → 1.5; 0–100 en forma lineal de 1.5 a 3.5.
  - `toneFor(puntaje: number | null): Tone`: `null` → `'sin'`; menos de 60 → `'bajo'`; 60 o más → `'alto'`.
  - `interface ScreenPoint extends MapPoint { px: number; py: number; r: number; tone: Tone }`.
  - `layoutMap(points: MapPoint[], width: number, height: number, margin = 24): ScreenPoint[]`:
    - `px = width/2 + x·(width/2 − margin)` y `py = height/2 + y·(height/2 − margin)`;
    - mantiene el orden de entrada.
  - `nearestPoint(points: ScreenPoint[], x: number, y: number, maxDist = 14): ScreenPoint | null`.
  - `topLinks(points: ScreenPoint[], n = 6): ScreenPoint[]`: los `n` de mayor puntaje que no son `null`.
  - `SemanticMap({ onOpen }: { onOpen: (jobId: number) => void })`, export default:
    - canvas con `role="img"` y `aria-label` "`{total}` ofertas; `{k}` con puntaje ≥ 60";
    - tooltip `role="tooltip"` con título, empresa y puntaje en mono;
    - alto de 420 px, o 300 px si `matchMedia('(max-width: 639px)')`.
  - `ArtFrame({ query, height, empty, children }: { query: UseQueryResult<unknown>; height: number; empty: boolean; children: ReactNode })` en `frontend/src/art/ArtFrame.tsx` (spec §5):
    - cargando: esqueleto `.glass` con una retícula de puntos tenue y `aria-busy="true"`;
    - error: tarjeta `.glass` con `errorMessage(query.error)` y un botón "Reintentar" que llama a `query.refetch()`;
    - `empty`: `EmptyState` "sin-ofertas" con enlace a Perfil;
    - en cualquier otro caso, `children`.
    - Lo reusan `SkillGraph` (Tarea 12) y `SignalFlow` (Tarea 14).

- [ ] **Step 1: Write the failing tests**

- `mapLayout.test.ts`:
  - `(0,0)` va al centro y `(1,-1)` va a `(width-24, 24)`;
  - radios y tonos en 0, 59, 60, 100 y `null`;
  - `nearestPoint` devuelve el punto a 10 px y `null` a 15 px;
  - `topLinks` excluye los `null` y ordena por puntaje descendente.
- `Home.test.tsx` (con `server.use` y 3 puntos):
  - `el mapa anuncia el resumen`: `getByRole('img', {name: /3 ofertas; 2 con puntaje/})`.
  - `sin ofertas en el mapa se ve el estado vacío`: el handler por defecto `{total:0}` muestra el texto de `EmptyState` "sin-ofertas" y no muestra el canvas.
  - `tocar dos veces abre el detalle`:
    - se mockea `getBoundingClientRect` del canvas a 600×420;
    - un `pointerdown` con `pointerType: 'touch'` en las coordenadas de pantalla del punto 1 muestra el tooltip "Oferta 1";
    - un segundo toque abre `role="dialog"`.
  - `con movimiento reducido no hay animación`: con `media.reducedMotion = true`, después del primer dibujo no hay más llamadas a `requestAnimationFrame`.
  - `si el mapa falla, se puede reintentar`:
    - el primer `GET /api/map` responde 500 con `{detail:"Falló el mapa"}` y el segundo, 3 puntos;
    - se ve "Falló el mapa" y, después de hacer clic en "Reintentar", el `img` del mapa.

- [ ] **Step 2: Run them and verify they fail**

Run: `cd frontend && npx vitest run src/art/mapLayout.test.ts src/views/Home.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement**

**Dibujo** (spec §2.1):
- anillos del perfil en el centro y líneas de 0.6 px al 22% `--silver` hacia `topLinks`;
- puntos según su tono: `'sin'` en `--glow` al 55%, `'bajo'` en `--silver` al 60%, `'alto'` en `--text` con anillo de halo;
- entrada de 900 ms desde el centro con `easeOutCubic`, y luego deriva de ±1.5 px con `sin(t + id)`.

**Interacción:**
- puntero `mouse`: hover con `nearestPoint` y clic para abrir;
- puntero `touch`: el primer toque fija el tooltip y el segundo toque sobre el mismo punto abre.

**Inicio:** mapa arriba, `StatusStrip` y lista de tarjetas debajo, sin cambios en la lógica del top.

- [ ] **Step 4: Run tests**

Run: `cd frontend && npx vitest run && npm run typecheck`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A frontend/src
git commit -m "feat(frontend): mapa semántico de ofertas en Inicio"
```

---

### Task 12: Grafo de habilidades y huella en Perfil

**Files:**
- Create: `frontend/src/art/skillGraphLayout.ts`, `frontend/src/art/SkillGraph.tsx`, `frontend/src/art/Fingerprint.tsx`
- Modify: `frontend/src/art/glyph.ts` (agregar `fingerprintPaths`), `frontend/src/views/Profile.tsx`
- Delete: `frontend/src/art/ProfileGlyph.tsx`
- Test: `frontend/src/art/skillGraphLayout.test.ts`, `frontend/src/art/glyph.test.ts`, `frontend/src/views/Profile.test.tsx`

**Interfaces:**
- Consumes:
  - `useSkillsGraph()` y `SkillsGraph` (Tarea 10);
  - `normalizeAreas` y `AREAS` de `glyph.ts`;
  - `mulberry32` y `seeded` de `random.ts`.
- Produces:
  - `interface GraphNode { id: string; kind: 'skill' | 'offer'; label: string; x: number; y: number; r: number; tiene?: boolean; puntaje?: number; jobId?: number }`. El `id` es `"s:" + nombre` o `"o:" + job_id`.
  - `layoutGraph(g: SkillsGraph, width: number, height: number, seed = 1): { nodes: GraphNode[]; links: { source: GraphNode; target: GraphNode }[] }`:
    - d3-force con `randomSource(mulberry32(seed))`, posiciones iniciales sembradas, 300 `tick()` con la simulación detenida, y cada nodo limitado a `[r+8, width−r−8] × [r+8, height−r−8]`;
    - radio de las habilidades `5 + 5·grado/maxGrado`, con mínimo 5; las ofertas miden 3.
  - `fingerprintPaths(axes: number[], radius: number, seed: string): string[]`: 6 sectores; en cada uno, de 3 a 7 arcos concéntricos cuyo largo es proporcional a `axes[i]`. Determinista.
  - `SkillGraph({ onOpen })` (export default) y `Fingerprint({ versions })` (export default).

- [ ] **Step 1: Write the failing tests**

- `skillGraphLayout.test.ts`:
  - `misma semilla, mismas posiciones`;
  - `todos los nodos dentro de los límites`;
  - `una arista por GraphEdge`;
  - `radio crece con el grado`.
- `glyph.test.ts`:
  - `fingerprintPaths es determinista` y devuelve más de 18 paths para 6 ejes no nulos;
  - con todos los ejes en 0, devuelve 6 paths mínimos sin `NaN`.
- `Profile.test.tsx`:
  - `el grafo muestra habilidades y faltantes`: con un handler de grafo, aparece la etiqueta "Java", y "Docker" aparece marcada como faltante (`data-tiene="false"` en su `<g>`).
  - `pasar sobre una habilidad atenúa el resto`: después de `hover` en Java, un nodo no conectado tiene `opacity` 0.2.
  - `con movimiento reducido no hay animación`: no hay `requestAnimationFrame`.

- [ ] **Step 2: Run them and verify they fail**

Run: `cd frontend && npx vitest run src/art src/views/Profile.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement**

- `SkillGraph` va en **SVG**, porque son pocos nodos y queda accesible: cada habilidad es un `<g role="button" tabindex=0 aria-label="Java: 7 ofertas">`.
- La entrada se hace con una transición de opacidad de 600 ms; con movimiento reducido no hay transición.
- `Fingerprint` usa `normalizeAreas(versions)` de la última versión y es un SVG de 160 px.
- `Profile.tsx` monta `Fingerprint` y `SkillGraph` en lugar de `ProfileGlyph` y `Constellation`.

- [ ] **Step 4: Run tests**

Run: `cd frontend && npx vitest run && npm run typecheck`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A frontend/src
git commit -m "feat(frontend): grafo de habilidades y huella generativa en Perfil"
```

---

### Task 13: Pipeline y estallido de partículas en Postulaciones

**Files:**
- Create: `frontend/src/art/pipelineLayout.ts`, `frontend/src/art/Pipeline.tsx`, `frontend/src/art/ParticleBurst.tsx`
- Modify: `frontend/src/views/Applications.tsx`
- Delete: `frontend/src/art/Garden.tsx`, `gardenLayout.ts`, `gardenLayout.test.ts`, `Starfall.tsx`
- Test: `frontend/src/art/pipelineLayout.test.ts`, `frontend/src/views/Applications.test.tsx`

**Interfaces:**
- Consumes: `ApplicationItem` (incluye `estado`, `seguimiento` y `creado_en`/`actualizado_en`, con los nombres que ya tiene `types.ts`).
- Produces:
  - `STAGES = ['guardada', 'aplicada', 'entrevista', 'oferta'] as const`.
  - `interface PipeNode { id: number; estado: Estado; x: number; y: number; seguimiento: boolean; titulo: string }`.
  - `layoutPipeline(apps: ApplicationItem[], width: number, height: number): { nodes: PipeNode[]; paths: { id: number; d: string }[] }`:
    - el 82% izquierdo del ancho se divide en 4 columnas iguales, y el 18% derecho es la columna de `rechazada`;
    - dentro de cada columna, los nodos van ordenados por fecha de creación ascendente y repartidos de forma uniforme en el alto;
    - cada nodo tiene un `path` Bézier que pasa por las columnas anteriores a su etapa, a la misma `y`. Para `rechazada`, el camino va de guardada a aplicada y de ahí a la columna lateral.
  - `ParticleBurst({ seed, onDone }: { seed: number; onDone: () => void })` (export default): un canvas `data-testid="burst"` `aria-hidden` con 60 partículas, que termina en 1.2 s.

- [ ] **Step 1: Write the failing tests**

- `pipelineLayout.test.ts`:
  - `cada etapa en su columna`: la x de `aplicada` es mayor que la de `guardada`;
  - `ordena por fecha dentro de la columna`;
  - `rechazada va a la columna lateral y no desplaza a las demás`: las `y` de los otros nodos son las mismas con o sin la rechazada;
  - `un path por nodo, sin NaN`.
- `Applications.test.tsx`:
  - renombrar `starfall` a `burst` y `jardín` a `pipeline` en los tests existentes;
  - `el pipeline tiene un botón por postulación`: los botones `Editar Oferta 10x` son 2;
  - `una rechazada sigue siendo editable`: con `application(3, 'rechazada')`, existe el botón "Editar Oferta 103".

- [ ] **Step 2: Run them and verify they fail**

Run: `cd frontend && npx vitest run src/art/pipelineLayout.test.ts src/views/Applications.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement**

- `Pipeline` es un **SVG**:
  - columnas con su encabezado en mono, paths de 1 px en `--line-strong` y nodos de 6 px en `--silver`;
  - los nodos con seguimiento laten (anillo con opacidad animada por CSS, desactivada con movimiento reducido);
  - cada nodo va envuelto en un `<button aria-label="Editar {titulo}">` dentro de `foreignObject`, o como `<g role="button" tabindex=0>` con Enter/Espacio, igual que hacía `Garden`.
- `Applications.tsx` cambia las pestañas a "Pipeline" y "Tablero", y el estallido a `ParticleBurst`.

- [ ] **Step 4: Run tests**

Run: `cd frontend && npx vitest run && npm run typecheck`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A frontend/src
git commit -m "feat(frontend): pipeline de postulaciones y estallido de partículas"
```

---

### Task 14: Flujo de señales en Explorar y limpieza final de piezas viejas

**Files:**
- Create: `frontend/src/art/SignalFlow.tsx`
- Modify: `frontend/src/art/river.ts` (`SOURCE_COLORS` con la paleta nueva), `frontend/src/views/Explore.tsx`, `frontend/src/views/Home.tsx` (si quedó alguna importación vieja)
- Delete: `frontend/src/art/OfferRiver.tsx`, `DailySky.tsx`, `sky.ts`, `sky.test.ts`, `Constellation.tsx`, `constellationLayout.ts`, `constellationLayout.test.ts`
- Modify: `README.md` (sección Dashboard: identidad nueva, piezas y solo modo oscuro)
- Test: `frontend/src/art/river.test.ts`, `frontend/src/views/Explore.test.tsx`

**Interfaces:**
- Consumes: `toSeries` de `river.ts` y `useFlow()`.
- Produces:
  - `SOURCE_COLORS = ['var(--silver)', 'var(--glow)', '#8FA3D6', '#5E6E9C', '#B4BED4', '#3E4F86']`.
  - `SignalFlow()` (export default): un SVG con el contorno de cada capa (1 px), relleno al 8%, una retícula horizontal de 4 líneas en `--line` y ejes en mono de 11 px.

- [ ] **Step 1: Write the failing tests**

- `river.test.ts`: `SOURCE_COLORS` tiene 6 elementos y no incluye `var(--accent)`.
- `Explore.test.tsx::muestra el flujo de ingesta`: con un handler de flujo de 3 semanas, existe `getByRole('img', {name: /flujo de ofertas/i})`.
- **Guardia de naturaleza** en un test nuevo, `src/art/naming.test.ts`: con `import.meta.glob('/src/**/*.{ts,tsx}', { query: '?raw', import: 'default', eager: true })`, ningún archivo contiene `/\b(garden|jard[ií]n|starfall|constellation|constelaci[oó]n|DailySky|NightGradient)\b/i`. El propio archivo del test queda excluido.

- [ ] **Step 2: Run them and verify they fail**

Run: `cd frontend && npx vitest run src/art src/views/Explore.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement** el componente y borra los archivos de la lista **Delete**. Actualiza el README.

- [ ] **Step 4: Full verification**

Run: `cd frontend && npx vitest run && npm run typecheck && npm run build`, then `cd ../backend && uv run pytest -q`
Expected: todo PASS y build OK.

- [ ] **Step 5: Commit**

```bash
git add -A frontend README.md
git commit -m "feat(frontend): flujo de señales en Explorar y retiro de las piezas de naturaleza"
```

---

### Task 15: Verificación en navegador

**Files:** ninguno, salvo los arreglos que salgan de la revisión. Cada uno se hace con su prueba primero y en un commit propio.

- [ ] **Step 1: Reconstruir y levantar**

Run: `docker compose up -d --build web`
Expected: `web` healthy; `curl -s localhost:8000/api/map` devuelve JSON.

- [ ] **Step 2: Datos reales, solo lectura** (navegador integrado, http://localhost:8000)

Recorrer Inicio, Explorar, Postulaciones y Perfil a 1280 px y a 360 px de ancho:
- sin scroll horizontal (`document.documentElement.scrollWidth <= innerWidth`);
- el mapa muestra puntos y su tooltip;
- el grafo tiene etiquetas legibles;
- no hay errores en la consola.

- [ ] **Step 3: DEMO_MODE para las interacciones**

Run: `DEMO_MODE=true docker compose up -d web`

Probar:
- 👎 con deshacer en Inicio;
- 👍 en el detalle de Explorar, que se marca al instante;
- mover una postulación a entrevista, que muestra el estallido;
- borrar una postulación, que pide confirmación;
- Escape cierra los diálogos.

Al terminar, volver a `docker compose up -d web` en modo normal.

- [ ] **Step 4: Commit de arreglos, si los hay**, y registro en el ledger.
