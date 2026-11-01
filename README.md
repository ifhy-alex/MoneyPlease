# MoneyPlease

Buscador personal de prácticas y empleo. Recolecta ofertas de fuentes legales (páginas de carreras en Greenhouse y Lever, la API de JSearch y las alertas de LinkedIn e Indeed que llegan por correo), las normaliza y las guarda en PostgreSQL.

Incluye la **Fase 1** (ingesta y base de datos) y la **Fase 2** (perfil desde el CV y matching con Gemini). El dashboard y el correo diario llegan en la Fase 3. El diseño está en [docs/superpowers/specs](docs/superpowers/specs).

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

## Fase 2: perfil y matching

Necesita `GEMINI_API_KEY` en `.env` (AI Studio, en un proyecto **sin facturación** para quedarse en el nivel gratuito). El CV y el perfil viven en `backend/private/`, que está en `.gitignore`.

1. Copiar el CV a `backend/private/cv.pdf`.
2. Generar el borrador del perfil. El texto del CV se redacta antes de enviarlo: sin nombre, correos, teléfonos ni enlaces. Lo que se envió queda en `backend/private/cv.txt`.
   ```bash
   docker compose exec worker python -m moneyplease profile from-cv private/cv.pdf
   ```
3. Revisar y editar `backend/private/profile.yaml`: skills, roles y sobre todo `preferences` (modalidad, provincias, palabras a excluir).
4. Guardar una versión nueva. Cada versión se evalúa desde cero.
   ```bash
   docker compose exec worker python -m moneyplease profile save
   ```
5. El worker corre el matching después de cada ingesta (6:00 y 18:00), con hasta 50 evaluaciones por corrida. A mano:
   ```bash
   docker compose exec worker python -m moneyplease match --limit 10
   docker compose exec worker python -m moneyplease top
   ```

### Punto de control

```bash
docker compose exec worker python -m moneyplease label <job_id> buena|regular|mala
docker compose exec worker python -m moneyplease eval
```

`eval` dice cuántas del top 10 marcaste como buenas o regulares. La meta es al menos 5.

La primera corrida calcula los embeddings de todas las ofertas en CPU y puede tardar bastante. Después solo procesa las nuevas. El modelo (`intfloat/multilingual-e5-small`) se descarga una sola vez en el volumen `hf_cache`.

## Dashboard

`docker compose up -d --build` levanta también el servicio `web`. Se abre en **http://localhost:8000**, que solo escucha en tu computadora y no tiene login.

La identidad es **medianoche y plata**: solo modo oscuro, tarjetas de vidrio sobre un campo de partículas, fuentes Geist y Geist Mono (incluidas en la app, sin internet). Todo el arte es algorítmico y usa tus datos reales; con "reducir movimiento" activado en el sistema, queda quieto.

- **Inicio:** el **mapa semántico** (tú en el centro y cada oferta a la distancia de su similitud real con tu perfil; al pasar o tocar se ve la oferta, al hacer clic se abre), el top con 👍 / 👎 / 🔖, las brechas de la semana, los recordatorios de seguimiento y el punto de control.
- **Explorar:** todas las ofertas, con filtros guardados en la URL, el **flujo de ingesta** por fuente y el detalle de cada una.
- **Postulaciones:** el **pipeline** (cada postulación es un nodo que avanza por las etapas) y un tablero kanban, que se puede arrastrar o mover con el teclado. Borrar pide confirmación.
- **Perfil:** subir el CV (genera un borrador sin guardarlo), editar con el formulario, el historial de versiones, la **huella** generativa y el **grafo de habilidades** (tus habilidades conectadas con las ofertas que las piden; punteadas, las que piden y te faltan).

### Universo 3D

Desde el mapa de Inicio (**Explorar en 3D**) o el grafo de Perfil (**Ver en 3D**) se abre `/universo`, una galaxia que se puede rotar, acercar y recorrer:

- **Ofertas:** cada estrella es una oferta. La distancia al centro (tú) es su similitud real con tu perfil, y las parecidas forman nubes con nombre (por ejemplo "Python · Java"). El panel tiene buscador (la cámara vuela a lo que buscas), filtros por puntaje, empresa y tipo, y la lista de nubes.
- **Habilidades:** tus habilidades en plata y las que piden y te faltan en rojo, conectadas con las ofertas que las piden. Al pasar sobre una se iluminan sus ofertas; al tocarla, el panel las lista.

Las publicaciones casi idénticas (misma empresa, mismo texto, como un puesto publicado dos veces) aparecen como una sola tarjeta con "+1 publicación casi idéntica", y 👍 / 👎 se aplica a todas.

Las etiquetas 👍 / 👎 sirven también como ejemplos para Gemini. A partir de 6 etiquetas (al menos 2 de cada tipo) ajustan el score en ±15 puntos, y el top se vuelve a evaluar cuando cambian.

### Modo demo

Para mostrar el dashboard sin tus datos, por ejemplo en un portafolio o una entrevista:

```bash
docker compose exec web python -m moneyplease demo seed
DEMO_MODE=true docker compose up -d web
```

Usa una base aparte (`moneyplease_demo`) con datos ficticios y no llama a Gemini. Para volver, `docker compose up -d web` sin la variable.

### Desarrollo del frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, con proxy de /api al servicio web
npm test
```
