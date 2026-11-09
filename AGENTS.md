# Instrucciones para agentes de IA

MoneyPlease es el buscador personal de prácticas y empleo junior de su dueño, estudiante de Informática Empresarial en la UCR (Costa Rica). Responde siempre en **español**. La guía para personas está en [docs/USO.md](docs/USO.md); este archivo es para ti.

## Mapa del proyecto

- `README.md` está en inglés (portafolio); la documentación operativa, en español, está en `docs/INSTALACION.md` y `docs/USO.md`.
- `backend/` — Python 3.12 con [uv](https://docs.astral.sh/uv/): FastAPI, SQLAlchemy 2, PostgreSQL 16 + pgvector, Gemini.
  - `moneyplease/ingest/` — conectores (Greenhouse, Lever, Workday, JSearch, alertas de Gmail) y normalización.
  - `moneyplease/matching/` — filtros del perfil, embeddings y evaluación con Gemini.
  - `moneyplease/__main__.py` — la CLI (`python -m moneyplease --help`).
- `frontend/` — React 19 + TypeScript + Vite + Tailwind; el build lo sirve el backend.
- `docker-compose.yml` — servicios `db`, `worker` (scheduler a las 6:00 y 18:00 de Costa Rica) y `web` (http://localhost:8000).
- `docs/superpowers/specs/` y `plans/` — diseño y planes de cada fase.

## Reglas que no se rompen

1. **No leas ni muestres** `backend/private/` (CV y perfil), `backend/secrets/` (tokens de Gmail) ni `.env` (keys). La app los usa sola; tú no los necesitas.
2. **No mandes datos personales del CV a ningún servicio.** La app solo envía a Gemini la vista sin datos de contacto (`Profile.llm_view`).
3. **Nunca borres la base de datos:** nada de `docker compose down -v`, borrar volúmenes ni "Reset to factory defaults" en Docker Desktop.
4. **Commits en español** con formato convencional (`fix(ingesta): …`, `feat(frontend): …`), **sin línea `Co-Authored-By`** ni atribución a IA. No hagas push ni publiques nada sin que el dueño lo pida.
5. Los cambios de código van con prueba primero (TDD); corre las suites antes de dar algo por terminado.

## Tarea frecuente: "trae ofertas y evalúalas"

Desde la raíz del repositorio:

1. **Comprueba los contenedores:** `docker compose ps -a`. Si `db`, `web` o `worker` no están *Up*, corre `docker compose up -d` y espera a que `db` diga *healthy* (unos segundos).
2. **Ingesta:** `docker compose exec worker python -m moneyplease ingest`. Revisa las líneas finales, una por fuente: anota las que tengan `ok=False` (con su error) y cuántas `nuevas` hubo en total y en `gmail`.
3. **Evaluación:** `docker compose exec worker python -m moneyplease match`. La última línea dice `embebidas candidatas evaluadas fallidas`; reporta si hubo `fallidas` o `cuota agotada`.
4. **Resultados:** `docker compose exec worker python -m moneyplease recientes --horas 1` lista lo recién evaluado (puntaje · fit · título — empresa | lugar | enlace). `top` da el top general.
5. **Reporta** al dueño: total de nuevas y cuántas por alertas de Gmail, fuentes con error, una tabla con las evaluadas de 60 o más (puntaje, oferta con enlace, lugar) y si el top cambió. Las de menos de 45 basta con resumirlas.

Si `docker compose exec` falla porque el contenedor no existe, usa la ruta con uv: `cd backend` y `uv run python -m moneyplease <comando>` (necesita la base de datos encendida igual).

### Errores conocidos

- `connection timeout expired`: la base de datos no está arriba o Docker acaba de arrancar. Levanta los contenedores y reintenta una vez.
- `gmail traidas=0` durante días: el problema suele estar en los filtros de Gmail, no en el código; avisa al dueño (ver docs/USO.md).
- Gmail con error de token: el dueño debe correr `uv run python -m moneyplease gmail-auth` (abre el navegador; no lo hagas tú).

## Tests

```bash
cd backend && uv run pytest -q          # levanta Postgres con testcontainers (ver docs/INSTALACION.md)
cd frontend && npx vitest run && npm run build
```

Después de cambiar código, reconstruye lo afectado: `docker compose up -d --build web worker`.
