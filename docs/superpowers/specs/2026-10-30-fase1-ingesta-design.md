# Fase 1 — Ingesta y base de datos

Fecha: 2026-10-30 · Plan madre: "Plan técnico: Buscador de prácticas y empleo"

## Objetivo

Que entren ofertas reales de práctica y empleo a una base PostgreSQL todos los días, sin intervención manual, desde fuentes legales. Es la base sobre la que se construyen el perfil y el matching (Fase 2), y el dashboard y el correo (Fase 3).

**Punto de control:** tras varios días con `docker compose up -d`, `python -m moneyplease stats` muestra ofertas reales nuevas cada día y al menos algunas ubicadas en Costa Rica.

## Contexto y supuestos

- Usuario: estudiante de Informática Empresarial en Costa Rica que busca práctica y luego empleo junior (presencial en el GAM, híbrido o remoto).
- Costo cero. Todo corre en Docker Compose en la computadora del usuario.
- Al iniciar no existe ninguna credencial (ni JSearch ni Gmail OAuth) ni lista de empresas. Por eso:
  - Greenhouse y Lever funcionan de verdad desde el inicio (no requieren llaves).
  - JSearch y Gmail se implementan y prueban con fixtures; se activan solos cuando sus credenciales aparecen en `.env`.
  - La lista semilla de empresas la arma el implementador verificando el ATS de cada una; el usuario la revisa.
- Python 3.12 gestionado con `uv` (el `python` por defecto de la máquina es 2.7).

## Arquitectura

Un solo paquete Python (`moneyplease`) con SQLAlchemy 2 + Alembic. Docker Compose con dos servicios:

- `db`: imagen `pgvector/pgvector:pg16`, volumen persistente.
- `worker`: el paquete, ejecuta `alembic upgrade head` al arrancar y luego el scheduler.

La API (FastAPI) se agrega en la Fase 3 dentro del mismo paquete y comparte los modelos.

```
MoneyPlease/
  docker-compose.yml
  .env.example                 DATABASE_URL, JSEARCH_API_KEY, GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH, GMAIL_LABEL
  .gitignore                   .env, secrets/, token*.json, __pycache__, .venv
  .github/workflows/ci.yml
  backend/
    Dockerfile
    pyproject.toml
    alembic.ini
    alembic/versions/
    companies.yaml
    moneyplease/
      __main__.py              CLI: ingest, stats, gmail-auth
      config.py                pydantic-settings, lee .env
      db/session.py            engine + sessionmaker
      db/models.py             Source, Job, IngestRun
      ingest/base.py           RawJob, Connector (Protocol), ConnectorResult
      ingest/http.py           cliente httpx compartido
      ingest/connectors/greenhouse.py
      ingest/connectors/lever.py
      ingest/connectors/jsearch.py
      ingest/connectors/gmail_alerts.py
      ingest/normalize.py
      ingest/sources.py        sincroniza companies.yaml y fuentes globales con la tabla sources
      ingest/run.py            orquesta una corrida
      scheduler.py             APScheduler
    tests/
      fixtures/                JSON de Greenhouse/Lever/JSearch, correos .eml de LinkedIn/Indeed
      ...
```

### Unidades y responsabilidades

| Unidad | Hace | Depende de |
| --- | --- | --- |
| `ingest/base.py` | Define `RawJob` (dataclass: source_key, external_id, title, company, location, description, url, published_at, raw) y el protocolo `Connector` con `key: str` y `fetch() -> list[RawJob]`, más `is_complete_listing: bool` | nada |
| `ingest/http.py` | Cliente httpx con user-agent identificable (`MoneyPlease/0.1 (+https://github.com/ifhy-alex/MoneyPlease)`), límite de 1 request/segundo por dominio, chequeo de `robots.txt` (cacheado por dominio), reintentos | httpx |
| Conectores | Traen y parsean una fuente. Nunca escriben en la base | `http.py`, `base.py` |
| `normalize.py` | `RawJob` → dict de columnas de `jobs`: limpia HTML de la descripción, deduce modalidad y provincia, calcula hash | `base.py` |
| `sources.py` | Crea/actualiza filas de `sources` desde `companies.yaml` y las fuentes globales (jsearch, gmail) | modelos, YAML |
| `run.py` | Corre conectores activos, upsert, expiración, registro en `ingest_runs` | todo lo anterior |
| `scheduler.py` | Dispara `run.py` según horario | APScheduler, `run.py` |

Los conectores son funciones puras sobre HTTP: se prueban sin base de datos. `run.py` es el único módulo que escribe.

## Modelo de datos (Fase 1)

Solo se crean las tablas que esta fase usa. `profiles`, `matches` y `applications` llegan con su fase, cada una en su propia migración.

La migración inicial ejecuta `CREATE EXTENSION IF NOT EXISTS vector`.

**`sources`**

| Campo | Tipo | Notas |
| --- | --- | --- |
| id | serial PK | |
| key | text único | `greenhouse:<slug>`, `lever:<slug>`, `jsearch`, `gmail` |
| nombre | text | |
| tipo | text | `ats`, `api`, `email`, `scraper` |
| config_json | jsonb | slug, URL de carreras, consulta, etc. |
| activa | bool | `false` si da 404 o se desactiva a mano |
| desactivada_motivo | text null | |

**`jobs`**

| Campo | Tipo | Notas |
| --- | --- | --- |
| id | serial PK | |
| source_id | FK sources | primera fuente que la trajo |
| external_id | text null | id en la fuente |
| titulo, empresa, ubicacion | text | |
| modalidad | text | `presencial`, `hibrido`, `remoto`, `desconocida` |
| provincia | text null | provincia de CR si se detecta |
| pais | text null | código ISO-2 si se detecta |
| descripcion | text | texto plano |
| url | text | |
| publicado_en | timestamptz null | |
| estado | text | `active`, `expired` |
| hash | text único | ver Normalización |
| raw_json | jsonb | payload crudo completo |
| embedding | vector(384) null | se llena en la Fase 2 |
| primera_vez_visto, ultima_vez_visto | timestamptz | |
| corridas_ausente | int, default 0 | |

Índices: `jobs(hash)` único, `jobs(estado, publicado_en)`, `jobs(source_id)`. El índice HNSW sobre `embedding` se crea en la Fase 2.

**`ingest_runs`**

| Campo | Tipo | Notas |
| --- | --- | --- |
| id | serial PK | |
| source_id | FK sources | |
| iniciado_en, terminado_en | timestamptz | |
| ok | bool | |
| ofertas_traidas | int | |
| ofertas_nuevas | int | |
| error | text null | |

Alimenta `stats`, la futura página de salud y la alerta de "0 ofertas en 2 corridas".

## Conectores

| Conector | Endpoint / origen | Listado completo | Activo cuando |
| --- | --- | --- | --- |
| Greenhouse | `GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true` | sí | la empresa está en `companies.yaml` con `ats: greenhouse` |
| Lever | `GET https://api.lever.co/v0/postings/{slug}?mode=json` | sí | ídem con `ats: lever` |
| JSearch | `GET https://jsearch.p.rapidapi.com/search` con consultas de práctica/junior en Costa Rica (`country=cr`) y remoto | no | existe `JSEARCH_API_KEY` |
| Gmail | Gmail API `users.messages.list` con `labelIds` = etiqueta `GMAIL_LABEL` (default `Empleo/Alertas`) y solo mensajes no procesados | no | existen credenciales y token OAuth |

**`companies.yaml`**

```yaml
- nombre: Ejemplo S.A.
  ats: greenhouse        # greenhouse | lever
  slug: ejemplo
  careers_url: https://...
  activa: true
```

La lista semilla tiene 15–20 empresas tecnológicas con operación en Costa Rica, cada una verificada contra su endpoint público antes de agregarla. Las empresas que usan Workday u otros ATS no soportados se anotan en un comentario para una fase futura.

**JSearch.** Una sola request por día (una consulta, una página), es decir unas 30 al mes de las 200 gratis. La consulta rota por día entre una lista fija en `config_json` (por ejemplo "practica profesional informatica Costa Rica", "junior developer Costa Rica", "intern software remote"). Las respuestas se guardan en `raw_json`, así que no hay que volver a pedirlas para re-procesar. Un HTTP 429 marca la fuente como "cuota agotada" hasta el día 1 del mes siguiente (guardado en `config_json`).

**Gmail.**
- Alcance `https://www.googleapis.com/auth/gmail.readonly`.
- `python -m moneyplease gmail-auth` corre el flujo OAuth local una vez y guarda el token en `secrets/` (ignorado por git).
- Como el alcance es de solo lectura, "procesado" no se marca en Gmail: se guarda en `config_json` el `internalDate` del mensaje más reciente procesado, y la siguiente corrida filtra con `after:<epoch>`.
- Parsers separados para correos de LinkedIn y de Indeed, cada uno probado con correos `.eml` reales guardados como fixtures (con datos personales removidos).

## Normalización

- **Descripción:** HTML → texto plano con BeautifulSoup.
- **Modalidad:** reglas por palabras clave en título, ubicación y descripción, en inglés y español (`remote`, `remoto`, `teletrabajo`, `hybrid`, `híbrido`, `on-site`, `presencial`). Si los campos estructurados de la fuente traen la modalidad (JSearch `job_is_remote`, Lever `workplaceType`), esos tienen prioridad. Si no se detecta nada, queda `desconocida`.
- **Provincia/país:** detecta "Costa Rica" y las siete provincias, más ciudades comunes del GAM (Escazú, Santa Ana, Heredia, Belén, Cartago, Alajuela, San Pedro, etc.) mapeadas a su provincia.
- **Hash:** `sha256(f"{empresa}|{titulo}|{ubicacion}")`, donde cada campo pasa a minúsculas, sin tildes, con espacios colapsados y sin puntuación.
- Nada se descarta en la ingesta. Filtrar es tarea del matching.

## Flujo de una corrida (`run.py`)

1. `sources.sync()`: refleja `companies.yaml` y las fuentes globales en la tabla `sources`.
2. Para cada fuente activa (o solo la pedida con `--source`):
   1. Abre un `ingest_runs` con `iniciado_en`.
   2. `fetch()`. Si lanza una excepción, cierra el run con `ok=false` y el error, y pasa a la siguiente fuente.
   3. Normaliza cada `RawJob`.
   4. Upsert por hash. Si la oferta es nueva, la inserta con `estado=active`. Si ya existía, actualiza `ultima_vez_visto`, `raw_json` y descripción, pone `corridas_ausente=0` y la reactiva si estaba `expired`.
   5. Si el conector es de listado completo y el fetch fue exitoso: a las ofertas `active` de esa fuente que no aparecieron les suma 1 a `corridas_ausente`. Al llegar a 2 pasan a `expired`.
   6. Cierra el run con `ok=true`, `ofertas_traidas` y `ofertas_nuevas`.
3. Cada fuente se procesa en su propia transacción.

## Scheduler

APScheduler (`BlockingScheduler`) con zona horaria `America/Costa_Rica`:

- Greenhouse, Lever y Gmail: 6:00 y 18:00.
- JSearch: una vez al día a las 6:00.
- `coalesce=True` y `max_instances=1` para que nunca se solapen corridas.

## CLI

- `python -m moneyplease ingest [--source KEY]`: corrida manual.
- `python -m moneyplease stats`: por fuente muestra activas, nuevas en las últimas 24 h, en Costa Rica, y el estado de la última corrida. Al final, los totales y las fuentes con 0 ofertas en sus 2 últimas corridas.
- `python -m moneyplease gmail-auth`: flujo OAuth inicial de Gmail.
- `python -m moneyplease worker`: arranca el scheduler (es lo que corre el contenedor).

## Manejo de errores

- Timeout o 5xx: hasta 3 reintentos con espera exponencial (1 s, 2 s, 4 s).
- 404 en Greenhouse/Lever: `activa=false` con `desactivada_motivo`, registrado en el run.
- 429 en JSearch: cuota agotada hasta el mes siguiente (ver Conectores).
- `robots.txt` que prohíbe la ruta: la fuente se desactiva con su motivo.
- Logging estándar de Python a stdout, visible con `docker compose logs worker`.

## Pruebas

- **pytest** con `respx` para simular httpx. Ningún test toca la red.
- **Conectores:** un test por conector con fixtures reales guardados una sola vez.
- **Normalizador:** tests de estabilidad del hash, de modalidad (inglés y español) y de detección de provincias.
- **`run.py`:** contra un Postgres real con pgvector (`testcontainers`): inserción, upsert, expiración tras 2 ausencias, no expirar si el fetch falló, reactivación, aislamiento de fallos entre fuentes.
- **CI:** GitHub Actions en cada push con `uv` y Python 3.12. Postgres corre como service container (`pgvector/pgvector:pg16`) y los tests de base leen `DATABASE_URL` de ahí. Localmente, si no hay `DATABASE_URL` de pruebas, usan testcontainers.

## Seguridad

- Secretos solo en `.env` y `secrets/`, ambos en `.gitignore`. `.env.example` sin valores reales.
- Token de Gmail con alcance de solo lectura y lectura limitada a una etiqueta.
- Los fixtures de correo se anonimizan antes de comitearlos.

## Fuera de alcance (fases posteriores)

Perfil y parseo del CV, embeddings, evaluación con LLM, API, frontend, resumen diario por correo, dedupe aproximado con `rapidfuzz`, bolsas locales (elempleo, Computrabajo, bolsa UCR), Adzuna, `DEMO_MODE`, respaldos con `pg_dump` y requisitos de la práctica UCR.
