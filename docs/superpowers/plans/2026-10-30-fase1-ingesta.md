# Fase 1 — Ingesta y base de datos: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un worker en Docker Compose que trae ofertas de Greenhouse, Lever, JSearch y alertas de Gmail dos veces al día, las normaliza, deduplica y guarda en PostgreSQL + pgvector, con un comando `stats` para medir el punto de control.

**Architecture:** Paquete Python `moneyplease` en `backend/`. Los conectores son funciones sobre HTTP que devuelven `ConnectorResult` y nunca tocan la base; `ingest/run.py` es el único que escribe. SQLAlchemy 2 + Alembic para el esquema; APScheduler para el horario.

**Tech Stack:** Python 3.12 (uv), SQLAlchemy 2, Alembic, psycopg 3, pgvector, pydantic-settings, httpx, respx, BeautifulSoup4, PyYAML, APScheduler 3, google-api-python-client + google-auth-oauthlib, pytest, testcontainers, Docker Compose, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-30-fase1-ingesta-design.md`

## Global Constraints

- Python 3.12 gestionado con `uv`; nunca usar el `python` del sistema (es 2.7). Comandos: `uv run ...` desde `backend/`.
- Costo cero: ninguna dependencia ni servicio de pago.
- Imagen de base de datos: `pgvector/pgvector:pg16`. URL con driver psycopg 3: `postgresql+psycopg://...`.
- User-agent: `MoneyPlease/0.1 (+https://github.com/ifhy-alex/MoneyPlease)`. Máximo 1 request/segundo por dominio. Respetar `robots.txt`.
- Zona horaria del scheduler: `America/Costa_Rica`.
- Secretos solo en `.env` y `secrets/`, ambos en `.gitignore`. Ningún test toca la red.
- Nombres de columnas en español tal como están en el spec (`titulo`, `empresa`, `ubicacion`, `modalidad`, `estado`, ...). Valores de `estado`: `active`, `expired`. Valores de `modalidad`: `presencial`, `hibrido`, `remoto`, `desconocida`.
- Commits terminan con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Rama: `fase1-ingesta`.

## Review Focus

1. **La misma oferta dos veces en un mismo fetch** (Greenhouse a veces repite una vacante en dos oficinas con la misma ubicación): se guarda una sola fila y no hay `IntegrityError`. Test en Task 8.
2. **Tildes y mayúsculas**: "Práctica Profesional - San José" y "practica profesional  san jose" producen el mismo hash. Test en Task 3.
3. **Campos ausentes** (`location` nulo, sin fecha de publicación, descripción vacía): normaliza sin excepción, `ubicacion=""`, `publicado_en=None`. Test en Task 3.
4. **Fechas en distintos formatos**: Lever da epoch en milisegundos, Greenhouse ISO con offset, JSearch epoch en segundos. Todas terminan como `datetime` con zona UTC. Tests en Tasks 5 y 6.
5. **Oferta vista por una segunda fuente**: si la trajo JSearch y luego aparece en Greenhouse, no se duplica, `ultima_vez_visto` se actualiza y `corridas_ausente` vuelve a 0. Test en Task 8.

---

## Estructura de archivos

```
.gitignore  .env.example  docker-compose.yml  .github/workflows/ci.yml
backend/
  Dockerfile  pyproject.toml  alembic.ini  companies.yaml
  alembic/env.py  alembic/versions/0001_inicial.py
  moneyplease/
    __init__.py  __main__.py  config.py  scheduler.py  stats.py
    db/__init__.py  db/session.py  db/models.py
    ingest/__init__.py  ingest/base.py  ingest/http.py  ingest/normalize.py
    ingest/sources.py  ingest/run.py
    ingest/connectors/__init__.py  greenhouse.py  lever.py  jsearch.py  gmail_alerts.py
    ingest/connectors/email_parsers.py
  tests/
    conftest.py
    fixtures/greenhouse_jobs.json  lever_postings.json  jsearch_search.json
    fixtures/linkedin_alert.eml  indeed_alert.eml
    test_config.py  test_migrations.py  test_normalize.py  test_http.py
    test_greenhouse.py  test_lever.py  test_jsearch.py  test_email_parsers.py  test_gmail.py
    test_sources.py  test_run.py  test_stats.py  test_cli.py
```

---

### Task 1: Esqueleto del proyecto, configuración y Docker Compose

**Files:**
- Create: `.gitignore`, `.env.example`, `docker-compose.yml`, `backend/Dockerfile`, `backend/pyproject.toml`, `backend/moneyplease/__init__.py`, `backend/moneyplease/config.py`
- Test: `backend/tests/test_config.py`

**Interfaces:**
- Produces: `moneyplease.config.Settings` (pydantic-settings, lee `.env` en la raíz del repo y variables de entorno) con campos `database_url: str = "postgresql+psycopg://moneyplease:moneyplease@localhost:5432/moneyplease"`, `jsearch_api_key: str | None = None`, `gmail_credentials_path: Path = Path("secrets/gmail_credentials.json")`, `gmail_token_path: Path = Path("secrets/gmail_token.json")`, `gmail_label: str = "Empleo/Alertas"`, `companies_path: Path = Path("companies.yaml")`, `timezone: str = "America/Costa_Rica"`. Función `get_settings() -> Settings`.

- [ ] **Step 1:** `uv init --package --python 3.12` dentro de `backend/` (nombre `moneyplease`), y `uv add sqlalchemy alembic "psycopg[binary]" pgvector pydantic-settings httpx beautifulsoup4 pyyaml apscheduler==3.* google-api-python-client google-auth-oauthlib`; `uv add --dev pytest respx testcontainers[postgres]`.
- [ ] **Step 2: Write the failing test** `tests/test_config.py::test_defaults_and_env_override`: con `monkeypatch.setenv("JSEARCH_API_KEY", "k")` y `monkeypatch.setenv("GMAIL_LABEL", "X")`, `Settings()` devuelve `jsearch_api_key == "k"`, `gmail_label == "X"` y `timezone == "America/Costa_Rica"`; sin esas variables, `jsearch_api_key is None`.
- [ ] **Step 3:** Run `uv run pytest tests/test_config.py -v` → FAIL (módulo no existe).
- [ ] **Step 4:** Implementar `config.py`. `.env.example` lista todas las variables con valores vacíos o de ejemplo. `.gitignore`: `.env`, `secrets/`, `token*.json`, `__pycache__/`, `.venv/`, `.pytest_cache/`.
- [ ] **Step 5:** `docker-compose.yml`: servicio `db` (`pgvector/pgvector:pg16`, usuario/clave/base `moneyplease`, volumen `pgdata`, puerto `5432:5432`, healthcheck `pg_isready`); servicio `worker` (build `backend/`, `env_file: .env`, `DATABASE_URL=postgresql+psycopg://moneyplease:moneyplease@db:5432/moneyplease`, monta `./secrets:/app/secrets:ro`, `depends_on: db: condition: service_healthy`, `restart: unless-stopped`, comando `sh -c "alembic upgrade head && python -m moneyplease worker"`). `Dockerfile` basado en `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`, `uv sync --frozen --no-dev`, `WORKDIR /app`.
- [ ] **Step 6:** Run `uv run pytest tests/test_config.py -v` → PASS. Run `docker compose config` → sin errores.
- [ ] **Step 7: Commit** `chore: esqueleto del proyecto, configuración y docker compose`.

---

### Task 2: Modelos, migración inicial y fixture de base de pruebas

**Files:**
- Create: `backend/moneyplease/db/__init__.py`, `db/session.py`, `db/models.py`, `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_inicial.py`, `backend/tests/conftest.py`
- Test: `backend/tests/test_migrations.py`

**Interfaces:**
- Consumes: `get_settings()` (Task 1).
- Produces:
  - `db.models`: `Base`, `Source`, `Job`, `IngestRun` con las columnas exactas del spec (sección "Modelo de datos"). `Job.embedding = mapped_column(Vector(384), nullable=True)`. `config_json`/`raw_json` son `JSONB`. Defaults: `Source.activa=True`, `Job.estado="active"`, `Job.corridas_ausente=0`, `Job.modalidad="desconocida"`.
  - `db.session.make_engine(url: str | None = None) -> Engine` y `make_session(url: str | None = None) -> sessionmaker[Session]`.
  - `tests/conftest.py`: fixture de sesión `db_url` (usa `TEST_DATABASE_URL` si existe; si no, levanta `PostgresContainer("pgvector/pgvector:pg16", driver="psycopg")`) que corre `alembic upgrade head` contra esa URL; fixture `session` por test que, al terminar, hace `TRUNCATE ingest_runs, jobs, sources RESTART IDENTITY CASCADE`.

- [ ] **Step 1: Write the failing tests** en `test_migrations.py`:
  - `test_tables_exist(session)`: `inspect(session.bind).get_table_names()` contiene `sources`, `jobs`, `ingest_runs`.
  - `test_vector_extension(session)`: `SELECT extname FROM pg_extension` contiene `vector`.
  - `test_job_hash_unique(session)`: insertar dos `Job` con el mismo `hash` lanza `IntegrityError`.
- [ ] **Step 2:** Run `uv run pytest tests/test_migrations.py -v` → FAIL.
- [ ] **Step 3:** Implementar modelos y `0001_inicial.py` escrito a mano (no autogenerate): `op.execute("CREATE EXTENSION IF NOT EXISTS vector")`, las tres tablas, índices `ix_jobs_estado_publicado (estado, publicado_en)`, `ix_jobs_source_id`, unique en `jobs.hash` y `sources.key`. `alembic/env.py` toma la URL de `-x url=...` o de `get_settings().database_url`.
- [ ] **Step 4:** Run `uv run pytest tests/test_migrations.py -v` → PASS (requiere Docker corriendo).
- [ ] **Step 5: Commit** `feat(db): modelos sources/jobs/ingest_runs y migración inicial`.

---

### Task 3: Tipos base y normalizador

**Files:**
- Create: `backend/moneyplease/ingest/__init__.py`, `ingest/base.py`, `ingest/normalize.py`
- Test: `backend/tests/test_normalize.py`

**Interfaces:**
- Produces:
  - `base.RawJob` (dataclass): `external_id: str | None`, `title: str`, `company: str`, `location: str | None`, `description: str` (puede ser HTML), `url: str`, `published_at: datetime | None`, `raw: dict`, `remote_hint: bool | None = None`, `workplace_hint: str | None = None`.
  - `base.ConnectorResult` (dataclass): `jobs: list[RawJob]`, `config_updates: dict = field(default_factory=dict)`.
  - `base.Connector` (Protocol): atributos `key: str`, `is_complete_listing: bool`; método `fetch() -> ConnectorResult`.
  - Excepciones en `base.py`: `SourceGone(Exception)` (404 o robots.txt prohibido; mensaje = motivo) y `QuotaExhausted(Exception)` con atributo `until: date`.
  - `normalize.canonical(text: str | None) -> str`: minúsculas, sin tildes (NFKD + quitar combinantes), sin puntuación, espacios colapsados, `strip`.
  - `normalize.job_hash(company: str, title: str, location: str | None) -> str`: `sha256` hex de `f"{canonical(company)}|{canonical(title)}|{canonical(location)}"`.
  - `normalize.html_to_text(html: str) -> str`: BeautifulSoup `get_text("\n")` con líneas vacías colapsadas.
  - `normalize.detect_modalidad(job: RawJob) -> str`: primero `remote_hint is True` → `remoto`; `workplace_hint` (`remote`/`hybrid`/`onsite`, valores de Lever) → `remoto`/`hibrido`/`presencial`; si no, palabras clave en título+ubicación+descripción: híbrido (`hybrid`, `híbrido`, `hibrido`) gana sobre remoto (`remote`, `remoto`, `teletrabajo`, `work from home`), y ambos sobre presencial (`on-site`, `onsite`, `presencial`, `in office`); si nada coincide → `desconocida`.
  - `normalize.detect_ubicacion(text: str) -> tuple[str | None, str | None]` → `(provincia, pais)`. Provincias: San José, Alajuela, Cartago, Heredia, Guanacaste, Puntarenas, Limón. Ciudades del GAM mapeadas: Escazú/Santa Ana/Curridabat/San Pedro/Montes de Oca/Tibás/Moravia/Desamparados/Pavas/Rohrmoser/La Sabana → San José; Belén/San Pablo/Santo Domingo/Barreal/Lagunilla/Ultrapark → Heredia; Coyol/El Coyol/Grecia → Alajuela; Tres Ríos/La Unión/Paraíso → Cartago. Coincidencia sobre `canonical`. Si encuentra provincia o "costa rica" → `pais="CR"`.
  - `normalize.normalize(job: RawJob) -> dict` con claves `external_id, titulo, empresa, ubicacion, modalidad, provincia, pais, descripcion, url, publicado_en, hash, raw_json`. `ubicacion = job.location or ""`. Si `published_at` es naive se asume UTC.

- [ ] **Step 1: Write the failing tests:**
  - `test_hash_ignores_accents_case_spacing`: `job_hash("ACME", "Práctica Profesional", "San José, CR") == job_hash("acme", "practica  profesional", "san jose cr")`.
  - `test_hash_differs_by_location`: distinta ubicación → distinto hash.
  - `test_modalidad_keywords` parametrizado: `("Backend Intern (Remote)", None) → "remoto"`, `("Desarrollador", "Híbrido - Heredia") → "hibrido"`, `("Dev", "Remote / Hybrid") → "hibrido"`, `("Analista", "On-site, Cartago") → "presencial"`, `("Analista", "Cartago") → "desconocida"`.
  - `test_modalidad_hints_win`: `remote_hint=True` con título "On-site" → `remoto`; `workplace_hint="hybrid"` → `hibrido`.
  - `test_detect_ubicacion` parametrizado: `"Escazú, San José"` → `("San José", "CR")`; `"Heredia, Costa Rica"` → `("Heredia", "CR")`; `"Costa Rica"` → `(None, "CR")`; `"Belén"` → `("Heredia", "CR")`; `"Remote - US"` → `(None, None)`.
  - `test_normalize_missing_fields`: `RawJob(location=None, published_at=None, description="")` → `ubicacion == ""`, `publicado_en is None`, `descripcion == ""`, sin excepción.
  - `test_normalize_strips_html`: descripción `"<p>Hola</p><ul><li>Python</li></ul>"` → contiene `"Hola"` y `"Python"`, no contiene `"<"`.
- [ ] **Step 2:** Run `uv run pytest tests/test_normalize.py -v` → FAIL.
- [ ] **Step 3:** Implementar `base.py` y `normalize.py`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `feat(ingest): tipos base y normalizador`.

---

### Task 4: Cliente HTTP respetuoso

**Files:**
- Create: `backend/moneyplease/ingest/http.py`
- Test: `backend/tests/test_http.py`

**Interfaces:**
- Consumes: `SourceGone` (Task 3).
- Produces: `class PoliteClient` con `__init__(self, *, min_interval: float = 1.0, retries: int = 3, backoff: float = 1.0, sleep: Callable[[float], None] = time.sleep, transport: httpx.BaseTransport | None = None)` y `get(self, url: str, *, params: dict | None = None, headers: dict | None = None, check_robots: bool = True) -> httpx.Response`. Comportamiento:
  - User-agent de Global Constraints, timeout 20 s.
  - Espera para que entre dos requests al mismo dominio pasen al menos `min_interval` segundos (usa `time.monotonic` y `sleep` inyectable).
  - Con `check_robots=True` descarga y cachea `https://<dominio>/robots.txt` por dominio (`urllib.robotparser`); si prohíbe la URL para el user-agent → `SourceGone("robots.txt prohíbe <url>")`. Si robots.txt da 404 o falla, se permite.
  - Timeout, error de conexión o 5xx: reintenta hasta `retries` veces con espera `backoff * 2**intento` (1, 2, 4 s). Agotados los reintentos, propaga la excepción (`httpx.HTTPStatusError` o la de red).
  - 404 → `SourceGone("404 <url>")`. Otros 4xx (incluido 429) → `response.raise_for_status()` sin reintentar.

- [ ] **Step 1: Write the failing tests** (respx, `sleep` falso que acumula esperas en una lista):
  - `test_sets_user_agent`: la request capturada tiene `User-Agent` que empieza con `MoneyPlease/0.1`.
  - `test_rate_limit_same_domain`: dos `get` seguidos al mismo dominio → el sleep falso recibió un valor > 0; a dominios distintos → no.
  - `test_retries_5xx_then_ok`: respuestas 503, 503, 200 → devuelve 200 y las esperas de backoff son `[1, 2]`.
  - `test_gives_up_after_retries`: siempre 500 → `httpx.HTTPStatusError`, 4 intentos en total.
  - `test_404_raises_source_gone`.
  - `test_429_not_retried`: 429 → `HTTPStatusError` con un solo intento.
  - `test_robots_disallow`: robots.txt `User-agent: *\nDisallow: /jobs` → `SourceGone` al pedir `/jobs/1`; robots.txt 404 → permitido.
- [ ] **Step 2:** Run `uv run pytest tests/test_http.py -v` → FAIL.
- [ ] **Step 3:** Implementar `PoliteClient`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `feat(ingest): cliente HTTP con rate limit, robots.txt y reintentos`.

---

### Task 5: Conectores Greenhouse y Lever

**Files:**
- Create: `backend/moneyplease/ingest/connectors/__init__.py`, `greenhouse.py`, `lever.py`, `backend/tests/fixtures/greenhouse_jobs.json`, `backend/tests/fixtures/lever_postings.json`
- Test: `backend/tests/test_greenhouse.py`, `backend/tests/test_lever.py`

**Interfaces:**
- Consumes: `PoliteClient` (Task 4), `RawJob`, `ConnectorResult` (Task 3).
- Produces:
  - `GreenhouseConnector(slug: str, company: str, client: PoliteClient)`, `key = f"greenhouse:{slug}"`, `is_complete_listing = True`. URL `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true`. Mapeo: `id→external_id`, `title`, `location.name→location`, `content` (viene con entidades HTML escapadas: aplicar `html.unescape` antes de guardar en `description`), `absolute_url→url`, `updated_at` (ISO con offset) → `published_at` en UTC. `company` sale del constructor.
  - `LeverConnector(slug: str, company: str, client: PoliteClient)`, `key = f"lever:{slug}"`, `is_complete_listing = True`. URL `https://api.lever.co/v0/postings/{slug}?mode=json`. Mapeo: `id`, `text→title`, `categories.location→location`, `descriptionPlain` + listas (`lists[].text` + `lists[].content`) → `description`, `hostedUrl→url`, `createdAt` (epoch ms) → UTC, `workplaceType→workplace_hint`.
  - Ambos con `check_robots=False`: son APIs JSON públicas pensadas para este uso, y sus robots.txt aplican al sitio web, no a la API.

- [ ] **Step 1:** Guardar fixtures reales: `curl` a un board público de cada ATS (por ejemplo una empresa de la lista semilla de Task 7), recortado a 3 ofertas. Si no hay red, construirlos con la forma documentada de cada API. No deben contener datos personales.
- [ ] **Step 2: Write the failing tests** (respx sirve el fixture):
  - `test_greenhouse_parses_jobs`: devuelve 3 `RawJob`; el primero tiene `external_id`, `url` que empieza con `https://`, `published_at.tzinfo` es UTC y la descripción no contiene `&lt;`.
  - `test_greenhouse_404_source_gone`.
  - `test_lever_parses_jobs`: 3 `RawJob`; `published_at == datetime.fromtimestamp(createdAt/1000, UTC)` del fixture; `workplace_hint` igual al del fixture.
  - `test_lever_404_source_gone`.
- [ ] **Step 3:** Run `uv run pytest tests/test_greenhouse.py tests/test_lever.py -v` → FAIL.
- [ ] **Step 4:** Implementar ambos conectores.
- [ ] **Step 5:** Run → PASS.
- [ ] **Step 6: Commit** `feat(ingest): conectores Greenhouse y Lever`.

---

### Task 6: Conector JSearch

**Files:**
- Create: `backend/moneyplease/ingest/connectors/jsearch.py`, `backend/tests/fixtures/jsearch_search.json`
- Test: `backend/tests/test_jsearch.py`

**Interfaces:**
- Consumes: `PoliteClient`, `RawJob`, `ConnectorResult`, `QuotaExhausted`.
- Produces: `JSearchConnector(api_key: str, config: dict, client: PoliteClient, today: date)`, `key = "jsearch"`, `is_complete_listing = False`.
  - `config["queries"]` (lista) y `config.get("query_index", 0)`. Elige `queries[query_index % len(queries)]`. Devuelve `config_updates={"query_index": query_index + 1}`.
  - Una request: `GET https://jsearch.p.rapidapi.com/search` con `params={"query": q, "page": 1, "num_pages": 1, "country": "cr", "date_posted": "week"}` y headers `X-RapidAPI-Key`, `X-RapidAPI-Host: jsearch.p.rapidapi.com`. `check_robots=False`.
  - Mapeo de `data[]`: `job_id`, `job_title`, `employer_name→company`, `job_city`/`job_state`/`job_country` unidos con `", "` sin vacíos → location, `job_description`, `job_apply_link→url`, `job_posted_at_timestamp` (segundos) → UTC, `job_is_remote→remote_hint`.
  - HTTP 429 → `QuotaExhausted(until=primer día del mes siguiente a today)`.
- Default de `queries` (lo crea `sources.py` en Task 7): `["practica profesional informatica Costa Rica", "junior developer Costa Rica", "intern software developer remote"]`.

- [ ] **Step 1: Write the failing tests:**
  - `test_rotates_query`: con `query_index=4` y 3 queries, la request lleva `query == queries[1]` y `config_updates == {"query_index": 5}`.
  - `test_parses_results`: fixture → `RawJob` con `remote_hint` y `published_at` en UTC; una ubicación con `job_state=None` no deja `", ,"`.
  - `test_429_quota_until_next_month`: `today=date(2026, 12, 15)` → `QuotaExhausted.until == date(2027, 1, 1)`.
- [ ] **Step 2:** Run `uv run pytest tests/test_jsearch.py -v` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `feat(ingest): conector JSearch con rotación de consultas y cuota`.

---

### Task 7: Conector Gmail, parsers de alertas y `gmail-auth`

**Files:**
- Create: `backend/moneyplease/ingest/connectors/email_parsers.py`, `gmail_alerts.py`, `backend/tests/fixtures/linkedin_alert.eml`, `backend/tests/fixtures/indeed_alert.eml`
- Test: `backend/tests/test_email_parsers.py`, `backend/tests/test_gmail.py`

**Interfaces:**
- Consumes: `RawJob`, `ConnectorResult`, `Settings`.
- Produces:
  - `email_parsers.parse_linkedin(html: str) -> list[RawJob]` y `parse_indeed(html: str) -> list[RawJob]`. Cada oferta: título, empresa, ubicación y URL (sin parámetros de tracking: quitar query string salvo el id de la oferta). `description=""`, `published_at=None` (el conector pone la fecha del correo). Si el HTML no tiene ofertas reconocibles → `[]` (nunca excepción).
  - `email_parsers.parse_alert(sender: str, html: str) -> list[RawJob]`: despacha por remitente (`linkedin.com` → LinkedIn, `indeed.com` → Indeed, otro → `[]`).
  - `GmailAlertsConnector(service, label: str, config: dict)`, `key = "gmail"`, `is_complete_listing = False`. `service` es el objeto de `googleapiclient` (inyectado para poder usar un falso en tests). Busca el id de la etiqueta por nombre, lista mensajes con `q=f"after:{config.get('last_internal_date_s', 0)}"` y `labelIds=[id]` (paginando), descarga cada uno en `format="full"`, toma la parte `text/html`, llama a `parse_alert` y asigna `published_at` = `internalDate` del correo. `config_updates={"last_internal_date_s": max(internalDate)//1000}` si hubo mensajes. `raw` incluye el id del mensaje.
  - `gmail_alerts.build_service(settings: Settings)`: carga el token de `gmail_token_path` y lo refresca si expiró. Si no existe el token, `None`.
  - `gmail_alerts.authorize(settings: Settings) -> None`: `InstalledAppFlow.from_client_secrets_file(gmail_credentials_path, ["https://www.googleapis.com/auth/gmail.readonly"]).run_local_server(port=0)` y guarda el token en `gmail_token_path`.

- [ ] **Step 1:** Crear los `.eml` de fixture con la estructura real de las alertas de LinkedIn ("Job alert") e Indeed: tabla de ofertas con título, empresa, ubicación y link, 2–3 ofertas cada una. Datos ficticios, sin información personal. Agregar `# TODO(usuario): reemplazar por un correo real anonimizado cuando lleguen las primeras alertas` como comentario en el test, porque los parsers de correo son lo que más probablemente se rompa.
- [ ] **Step 2: Write the failing tests:**
  - `test_parse_linkedin_fixture`: N ofertas con título, empresa y `url` sin `trackingId`.
  - `test_parse_indeed_fixture`: N ofertas.
  - `test_parse_unknown_sender_empty` y `test_parse_garbage_html_empty`: `parse_alert("x@y.com", "<html>")` → `[]`.
  - `test_gmail_connector_uses_after_and_updates_cursor`: `service` falso (objetos simples que imitan `users().labels().list().execute()` y `users().messages()...`) con dos mensajes. La query enviada contiene `after:1700000000` cuando `config={"last_internal_date_s": 1700000000}`; `config_updates["last_internal_date_s"]` es el mayor `internalDate // 1000`; `published_at` viene del `internalDate`.
  - `test_gmail_connector_no_messages`: lista vacía → `ConnectorResult([], {})`.
- [ ] **Step 3:** Run `uv run pytest tests/test_email_parsers.py tests/test_gmail.py -v` → FAIL.
- [ ] **Step 4:** Implementar.
- [ ] **Step 5:** Run → PASS.
- [ ] **Step 6: Commit** `feat(ingest): conector de alertas por Gmail y parsers LinkedIn/Indeed`.

---

### Task 8: Fuentes, `companies.yaml` y orquestador de corridas

**Files:**
- Create: `backend/companies.yaml`, `backend/moneyplease/ingest/sources.py`, `backend/moneyplease/ingest/run.py`
- Modify: `backend/moneyplease/ingest/connectors/__init__.py` (agregar `build_connector`)
- Test: `backend/tests/test_sources.py`, `backend/tests/test_run.py`

**Interfaces:**
- Consumes: modelos (Task 2), `normalize` (Task 3), `PoliteClient` (Task 4), los cuatro conectores (Tasks 5–7), `Settings`.
- Produces:
  - `sources.load_companies(path: Path) -> list[dict]` y `sources.sync(session: Session, settings: Settings) -> None`: upsert de una `Source` por empresa (`key=f"{ats}:{slug}"`, `tipo="ats"`, `config_json={"slug", "careers_url"}`, `activa` del YAML), más `jsearch` (`tipo="api"`, `config_json={"queries": [...defaults de Task 6]}` solo al crearla) y `gmail` (`tipo="email"`). No pisa `config_json` de estado (`query_index`, `last_internal_date_s`, `quota_exhausted_until`) ni reactiva una fuente desactivada por 404 (`desactivada_motivo` no nulo) salvo que su `activa` cambie en el YAML de false a true. Empresas que ya no están en el YAML → `activa=False`, `desactivada_motivo="quitada de companies.yaml"`.
  - `connectors.build_connector(source: Source, settings: Settings, client: PoliteClient, today: date) -> Connector | None`: `None` si falta la credencial (sin `jsearch_api_key`, o `build_service` devuelve `None`) o si `config_json["quota_exhausted_until"] > today`.
  - `run.run_ingest(session_factory: sessionmaker, settings: Settings, *, only: str | None = None, exclude: set[str] | None = None, connector_factory=build_connector, now: Callable[[], datetime] = utcnow) -> list[IngestRun]`. Algoritmo del spec ("Flujo de una corrida"), con estas decisiones:
    - Una transacción por fuente. Si `fetch()` falla, se hace rollback de esa fuente y se guarda su `IngestRun(ok=False, error=str(exc))` en una transacción aparte.
    - `SourceGone` → además `source.activa=False`, `desactivada_motivo=str(exc)`. `QuotaExhausted` → `config_json["quota_exhausted_until"]=exc.until.isoformat()`.
    - Dedupe dentro del batch por hash antes de escribir (la última aparición gana). Upsert con `insert(...).on_conflict_do_update(index_elements=["hash"], ...)`: al actualizar se cambian `ultima_vez_visto`, `raw_json`, `descripcion`, `corridas_ausente=0`, `estado='active'`, y se conserva `source_id` y `primera_vez_visto`. `ofertas_nuevas` = filas insertadas (`RETURNING (xmax = 0)`).
    - Expiración solo si `connector.is_complete_listing` y el fetch fue ok: `UPDATE jobs SET corridas_ausente = corridas_ausente + 1, estado = CASE WHEN corridas_ausente + 1 >= 2 THEN 'expired' ELSE estado END WHERE source_id = :sid AND estado = 'active' AND hash NOT IN (:vistos)`.
    - `config_updates` se mezclan en `source.config_json` (reasignando el dict para que SQLAlchemy detecte el cambio).
    - Fuente con `build_connector → None`: se salta sin crear `IngestRun`.
  - `companies.yaml`: 15–20 empresas tecnológicas con operación en Costa Rica, cada una verificada con un `GET` real a su endpoint de Greenhouse o Lever (respuesta 200 con ≥1 oferta o lista vacía válida). Las que usan Workday u otro ATS van en un bloque comentado `# Pendiente (ATS no soportado): ...`.

- [ ] **Step 1: Write the failing tests** en `test_sources.py`: `test_sync_creates_sources`, `test_sync_keeps_state_config` (con `query_index=7` previo, después de `sync` sigue en 7), `test_sync_deactivates_removed_company`, `test_sync_does_not_reactivate_404_source`.
- [ ] **Step 2: Write the failing tests** en `test_run.py`, con un `connector_factory` falso que devuelve conectores en memoria por `source.key`:
  - `test_inserts_new_jobs`: 2 ofertas → 2 filas `active`, `IngestRun(ok=True, ofertas_traidas=2, ofertas_nuevas=2)`.
  - `test_upsert_same_hash_twice_in_batch` (Review Focus 1): batch con dos `RawJob` con el mismo hash → 1 fila, sin error.
  - `test_second_run_updates_not_duplicates`: misma oferta en dos corridas → 1 fila, `ofertas_nuevas=0` en la segunda, `ultima_vez_visto` avanza.
  - `test_expires_after_two_missing_runs`: corrida 1 con A y B; corridas 2 y 3 solo con A → B queda `expired` después de la 3 y no después de la 2.
  - `test_failed_fetch_does_not_expire`: corrida 1 con A; corridas 2 y 3 lanzan `httpx.ConnectError` → A sigue `active` con `corridas_ausente == 0`.
  - `test_incomplete_listing_never_expires`: fuente `jsearch` con A y luego vacía 3 veces → A sigue `active`.
  - `test_reactivates_expired`: B expirada que reaparece → `active`, `corridas_ausente=0`.
  - `test_failure_isolated`: fuente 1 lanza excepción y fuente 2 ok → los jobs de la 2 están guardados; hay un run `ok=False` con el error.
  - `test_source_gone_deactivates` y `test_quota_exhausted_sets_until`.
  - `test_seen_by_second_source_resets` (Review Focus 5): A llega por `jsearch`; luego `greenhouse:x` trae el mismo hash → 1 fila, `source_id` sigue siendo el de jsearch, `corridas_ausente=0`.
  - `test_config_updates_merged`: el conector devuelve `{"query_index": 3}` → `source.config_json["query_index"] == 3` y las otras claves se conservan.
- [ ] **Step 3:** Run `uv run pytest tests/test_sources.py tests/test_run.py -v` → FAIL.
- [ ] **Step 4:** Implementar `sources.py`, `build_connector` y `run.py`.
- [ ] **Step 5:** Run → PASS.
- [ ] **Step 6:** Armar `companies.yaml` verificando cada slug con un request real (el implementador sí usa red en este paso, fuera de los tests).
- [ ] **Step 7: Commit** `feat(ingest): sincronización de fuentes, lista semilla y orquestador de corridas`.

---

### Task 9: CLI, `stats`, scheduler y prueba de humo con Docker

**Files:**
- Create: `backend/moneyplease/__main__.py`, `backend/moneyplease/stats.py`, `backend/moneyplease/scheduler.py`
- Test: `backend/tests/test_stats.py`, `backend/tests/test_cli.py`

**Interfaces:**
- Consumes: `run_ingest`, `sync`, `authorize`, `make_session`, `get_settings`.
- Produces:
  - CLI con `argparse`: `ingest [--source KEY]`, `stats`, `gmail-auth`, `worker`. `ingest` imprime una línea por `IngestRun` (`key ok traidas nuevas error`).
  - `stats.collect(session: Session, now: datetime) -> list[SourceStats]`, donde `SourceStats` es un dataclass con `key, activa, ofertas_activas, nuevas_24h, en_cr, ultima_corrida_ok: bool | None, ultima_corrida_en: datetime | None, cero_en_dos_ultimas: bool`. `en_cr` cuenta las ofertas `active` con `pais='CR'` de esa fuente. `cero_en_dos_ultimas` es True si las dos últimas corridas ok tuvieron `ofertas_traidas == 0`. `stats.render(rows) -> str` arma una tabla de texto con una fila de totales al final y luego la lista de fuentes con `cero_en_dos_ultimas`.
  - `scheduler.build_scheduler(settings) -> BlockingScheduler` con zona `America/Costa_Rica`: job `ingesta` con `CronTrigger(hour="6,18")` que corre todas las fuentes excepto `jsearch`; job `jsearch` con `CronTrigger(hour=6, minute=5)` y `only="jsearch"`. Ambos con `coalesce=True`, `max_instances=1`, `misfire_grace_time=3600`. El primer job llama a `run_ingest(..., exclude={"jsearch"})`.
  - `__main__.py` configura `logging.basicConfig(level=INFO, stream=sys.stdout, format="%(asctime)s %(levelname)s %(name)s: %(message)s")`; `run.py` registra con `logging.getLogger(__name__)` el inicio y fin de cada fuente y los errores.

- [ ] **Step 1: Write the failing tests:**
  - `test_stats_counts` (sesión de BD): 2 fuentes, ofertas con y sin `pais='CR'`, una creada hace 30 h → `nuevas_24h` y `en_cr` correctos.
  - `test_stats_zero_two_runs`: dos `IngestRun` ok con 0 ofertas → `cero_en_dos_ultimas is True`; si una de las dos falló, se mira la anterior ok.
  - `test_render_has_totals`: el texto contiene `TOTAL`.
  - `test_scheduler_jobs`: `build_scheduler` tiene los jobs `ingesta` y `jsearch` con las horas indicadas y la zona `America/Costa_Rica`.
  - `test_cli_ingest_calls_run` (monkeypatch `run_ingest`): `main(["ingest", "--source", "lever:x"])` lo llama con `only="lever:x"`.
- [ ] **Step 2:** Run `uv run pytest tests/test_stats.py tests/test_cli.py -v` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Run `uv run pytest -v` (toda la suite) → PASS.
- [ ] **Step 5: Prueba de humo:** `docker compose up -d --build`, luego `docker compose exec worker python -m moneyplease ingest` y `docker compose exec worker python -m moneyplease stats`. Esperado: las fuentes Greenhouse/Lever con `ok` y ofertas > 0 en al menos varias empresas; `jsearch` y `gmail` no aparecen (no hay credenciales); `docker compose logs worker` muestra el scheduler con las próximas ejecuciones.
- [ ] **Step 6: Commit** `feat: CLI, stats y scheduler`.

---

### Task 10: CI y README

**Files:**
- Create: `.github/workflows/ci.yml`, `README.md`

**Interfaces:**
- Consumes: la suite de tests y el fixture `db_url` (Task 2), que usa `TEST_DATABASE_URL` si existe.

- [ ] **Step 1:** `ci.yml`: en `push` y `pull_request`; job `test` en `ubuntu-latest` con service `postgres` (`pgvector/pgvector:pg16`, usuario/clave/base `test`, puerto 5432, health check `pg_isready`); pasos `actions/checkout@v4`, `astral-sh/setup-uv@v5`, `uv sync` en `backend/`, `uv run pytest -v` con `TEST_DATABASE_URL=postgresql+psycopg://test:test@localhost:5432/test`.
- [ ] **Step 2:** `README.md` breve en español: qué es, requisitos (Docker, uv), `cp .env.example .env`, `docker compose up -d`, comandos `ingest`/`stats`, cómo activar JSearch (poner la key) y Gmail (credenciales OAuth en `secrets/`, correr `gmail-auth` localmente con `uv run python -m moneyplease gmail-auth`), y cómo agregar empresas a `companies.yaml`.
- [ ] **Step 3:** Verificar localmente que la suite pasa con `TEST_DATABASE_URL` apuntando al `db` de compose: `TEST_DATABASE_URL=postgresql+psycopg://moneyplease:moneyplease@localhost:5432/moneyplease_test uv run pytest -v` (crear antes la base `moneyplease_test`). → PASS.
- [ ] **Step 4: Commit** `ci: tests en GitHub Actions y README`.
- [ ] **Step 5:** El push y el PR los decide el usuario; no hacer push sin su confirmación.
