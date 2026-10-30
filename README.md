# MoneyPlease

Buscador personal de prácticas y empleo. Recolecta ofertas de fuentes legales (páginas de carreras en Greenhouse y Lever, la API de JSearch y las alertas de LinkedIn e Indeed que llegan por correo), las normaliza y las guarda en PostgreSQL.

Esta es la **Fase 1: ingesta y base de datos**. El perfil, el matching, el dashboard y el correo diario llegan en fases posteriores. El diseño está en [docs/superpowers/specs](docs/superpowers/specs).

## Requisitos

- Docker con Docker Compose
- [uv](https://docs.astral.sh/uv/) (solo para correr comandos y tests fuera de Docker)

## Arranque

```bash
cp .env.example .env
docker compose up -d --build
```

El worker aplica las migraciones y deja programada la ingesta a las 6:00 y 18:00 (hora de Costa Rica). JSearch corre una vez al día, a las 6:05.

## Comandos

```bash
docker compose exec worker python -m moneyplease ingest
docker compose exec worker python -m moneyplease ingest --source greenhouse:konradgroup
docker compose exec worker python -m moneyplease stats
docker compose logs -f worker
```

`stats` muestra por fuente las ofertas activas, las nuevas en 24 h, las ubicadas en Costa Rica y el estado de la última corrida. Al final lista las fuentes que trajeron 0 ofertas en sus dos últimas corridas.

## Empresas

Se agregan en [backend/companies.yaml](backend/companies.yaml). Antes de agregar una, verificar que su endpoint responda:

- Greenhouse: `https://boards-api.greenhouse.io/v1/boards/<slug>/jobs`
- Lever: `https://api.lever.co/v0/postings/<slug>?mode=json`

Una empresa que da 404 se desactiva sola. Para reactivarla, poner `activa: false`, dejar pasar una corrida y volver a `activa: true`.

## Activar JSearch

1. Crear una cuenta gratis en RapidAPI y suscribirse al plan gratuito de JSearch (200 requests al mes).
2. Poner la key en `.env` como `JSEARCH_API_KEY=...`.
3. `docker compose up -d` para que el worker la tome.

## Activar las alertas de Gmail

1. En el correo dedicado, crear las alertas de LinkedIn e Indeed y un filtro que les ponga la etiqueta `Empleo/Alertas`.
2. En Google Cloud, crear un proyecto, habilitar la Gmail API y crear credenciales OAuth de tipo "Aplicación de escritorio". Descargar el JSON como `backend/secrets/gmail_credentials.json`.
3. Autorizar una vez desde tu computadora (abre el navegador):

   ```bash
   cd backend
   uv run python -m moneyplease gmail-auth
   ```

   El token queda en `backend/secrets/gmail_token.json`, con permiso de solo lectura. La carpeta `secrets/` está en `.gitignore` y el contenedor la monta como solo lectura.
4. `docker compose restart worker`.

## Tests

```bash
cd backend
uv run pytest
```

Los tests de base de datos levantan un Postgres con pgvector usando testcontainers (requiere Docker). Para usar una base existente, definir `TEST_DATABASE_URL`. Ningún test usa la red.
