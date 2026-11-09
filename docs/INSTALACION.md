# Instalación y configuración

Cómo levantar MoneyPlease desde cero y configurar cada fuente. Para el uso del día a día (traer y evaluar ofertas, ver resultados, problemas comunes) ver [USO.md](USO.md). El diseño de cada fase está en [superpowers/specs](superpowers/specs).

## Requisitos

- Docker con Docker Compose
- [uv](https://docs.astral.sh/uv/) (solo para correr comandos y tests fuera de Docker)

## Arranque

```bash
cp .env.example .env
docker compose up -d --build
```

Levanta tres servicios: `db` (PostgreSQL 16 + pgvector), `worker` (aplica las migraciones y programa la ingesta a las 6:00 y 18:00, hora de Costa Rica; JSearch una vez al día, a las 6:05) y `web` (API y dashboard en **http://localhost:8000**, que solo escucha en tu computadora y no tiene login).

## Comandos

```bash
docker compose exec worker python -m moneyplease ingest
docker compose exec worker python -m moneyplease ingest --source greenhouse:konradgroup
docker compose exec worker python -m moneyplease stats
docker compose logs -f worker
```

`stats` muestra por fuente las ofertas activas, las nuevas en 24 h, las ubicadas en Costa Rica y el estado de la última corrida. Al final lista las fuentes que trajeron 0 ofertas en sus dos últimas corridas.

## Empresas

Se agregan en [backend/companies.yaml](../backend/companies.yaml). Antes de agregar una, verificar que su endpoint responda:

- Greenhouse: `https://boards-api.greenhouse.io/v1/boards/<slug>/jobs`
- Lever: `https://api.lever.co/v0/postings/<slug>?mode=json`
- Workday: el sitio público de empleo (`https://<slug>.<wd>.myworkdayjobs.com/<site>`), con `wd` y `site` en el YAML. Revisar antes su `robots.txt`: si prohíbe el sitio de empleo, la empresa no se agrega. De Workday solo se guardan las ofertas en Costa Rica.

Una empresa que da 404 se desactiva sola. Para reactivarla, poner `activa: false`, dejar pasar una corrida y volver a `activa: true`.

## Activar JSearch

1. Crear una cuenta gratis en RapidAPI y suscribirse al plan gratuito de JSearch (200 requests al mes).
2. Poner la key en `.env` como `JSEARCH_API_KEY=...`.
3. `docker compose up -d` para que el worker la tome.

## Activar las alertas de Gmail

1. En el correo dedicado, crear un filtro que ponga la etiqueta `Empleo/Alertas` a las alertas de LinkedIn e Indeed. Si las alertas llegan a otro correo, reenviarlas con un filtro (el reenvío automático conserva el remitente original, que es como la app reconoce cada alerta). Los detalles están en [USO.md](USO.md#alertas-de-linkedin-por-correo).
2. En Google Cloud, crear un proyecto, habilitar la Gmail API y crear credenciales OAuth de tipo "Aplicación de escritorio". Descargar el JSON como `backend/secrets/gmail_credentials.json`. Publicar la app (pantalla de consentimiento en producción) para que el token no venza cada 7 días.
3. Autorizar una vez desde tu computadora (abre el navegador):

   ```bash
   cd backend
   uv run python -m moneyplease gmail-auth
   ```

   El token queda en `backend/secrets/gmail_token.json`, con permiso de solo lectura. La carpeta `secrets/` está en `.gitignore` y el contenedor la monta como solo lectura.
4. `docker compose restart worker`.

## Perfil y matching

Necesita `GEMINI_API_KEY` en `.env` (AI Studio, en un proyecto **sin facturación** para quedarse en el nivel gratuito). El CV y el perfil viven en `backend/private/`, que está en `.gitignore`.

1. Copiar el CV a `backend/private/cv.pdf`.
2. Generar el borrador del perfil. El texto del CV se redacta antes de enviarlo: sin nombre, correos, teléfonos ni enlaces. Lo que se envió queda en `backend/private/cv.txt`.
   ```bash
   docker compose exec worker python -m moneyplease profile from-cv private/cv.pdf
   ```
3. Revisar y editar `backend/private/profile.yaml`: skills, roles y sobre todo `preferences` (modalidad, provincias, provincias para ofertas sin modalidad, palabras a excluir).
4. Guardar una versión nueva. Cada versión se evalúa desde cero.
   ```bash
   docker compose exec worker python -m moneyplease profile save
   ```
5. El worker corre el matching después de cada ingesta (6:00 y 18:00), con hasta 50 evaluaciones por corrida. A mano:
   ```bash
   docker compose exec worker python -m moneyplease match --limit 10
   docker compose exec worker python -m moneyplease top
   docker compose exec worker python -m moneyplease recientes
   ```

También se puede subir el CV y editar el perfil desde el dashboard, en **Perfil**.

La primera corrida calcula los embeddings de todas las ofertas en CPU y puede tardar bastante. Después solo procesa las nuevas. El modelo (`intfloat/multilingual-e5-small`) se descarga una sola vez en el volumen `hf_cache`.

### Punto de control

```bash
docker compose exec worker python -m moneyplease label <job_id> buena|regular|mala
docker compose exec worker python -m moneyplease eval
```

`eval` dice cuántas del top 10 marcaste como buenas o regulares. La meta es al menos 5.

Las etiquetas 👍 / 👎 del dashboard sirven también como ejemplos para Gemini. A partir de 6 etiquetas (al menos 2 de cada tipo) ajustan el score en ±15 puntos, y el top se vuelve a evaluar cuando cambian.

## Dashboard

La identidad es **medianoche y plata**: solo modo oscuro, tarjetas de vidrio sobre un campo de partículas, fuentes Geist y Geist Mono (incluidas en la app, sin internet). Todo el arte es algorítmico y usa tus datos reales; con "reducir movimiento" activado en el sistema, queda quieto.

- **Inicio:** el **mapa semántico** (tú en el centro y cada oferta a la distancia de su similitud real con tu perfil), el top con 👍 / 👎 / 🔖, las brechas de la semana, los recordatorios de seguimiento y el punto de control.
- **Explorar:** todas las ofertas, con filtros guardados en la URL, el **flujo de ingesta** por fuente y el detalle de cada una. Cada tarjeta dice cuándo se publicó (en rojo si tiene más de 30 días).
- **Postulaciones:** el **pipeline** (cada postulación es un nodo que avanza por las etapas) y un tablero kanban, que se puede arrastrar o mover con el teclado.
- **Perfil:** subir el CV, editar con el formulario, el historial de versiones, la **huella** generativa y el **grafo de habilidades**.
- **Universo 3D** (`/universo`): una galaxia que se puede rotar y acercar. En **Ofertas**, cada estrella es una oferta a la distancia de su similitud con tu perfil, agrupadas en nubes con nombre; en **Habilidades**, tus habilidades en plata y las que te faltan en rojo, conectadas con las ofertas que las piden.

Las publicaciones casi idénticas (misma empresa, mismo texto) aparecen como una sola tarjeta con "+1 publicación casi idéntica", y 👍 / 👎 se aplica a todas.

### En el teléfono

Con [Tailscale](https://tailscale.com) en la computadora y el teléfono (misma cuenta), y HTTPS activado en la consola de Tailscale:

```bash
tailscale serve --bg 8000
```

La dirección `https://<pc>.<red>.ts.net` solo la ven tus dispositivos. Desde el navegador del teléfono, "Agregar a pantalla de inicio" la instala como app. No usar `tailscale funnel`, que la haría pública.

### Modo demo

Para mostrar el dashboard sin tus datos, por ejemplo en un portafolio o una entrevista:

```bash
docker compose exec web python -m moneyplease demo seed
DEMO_MODE=true docker compose up -d web
```

Usa una base aparte (`moneyplease_demo`) con datos ficticios y no llama a Gemini. Para volver, `docker compose up -d web` sin la variable.

## Tests

```bash
cd backend && uv run pytest
cd frontend && npm test && npm run typecheck && npm run build
```

Los tests de base de datos levantan un Postgres con pgvector usando testcontainers (requiere Docker). Para usar una base existente, definir `TEST_DATABASE_URL`. Ningún test usa la red. GitHub Actions corre las dos suites en cada push.

## Desarrollo del frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, con proxy de /api al servicio web
npm test
```

Los íconos de la app instalable se generan con `uv run --project ../backend python scripts/icons.py`.
