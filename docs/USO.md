# Uso diario de MoneyPlease

Guía para traer ofertas, evaluarlas y revisar los resultados sin ayuda. Los comandos se escriben en una terminal (PowerShell o Git Bash) **dentro de la carpeta `C:\dev\MoneyPlease`**.

## Qué hace la app sola

Mientras la computadora esté encendida y Docker abierto:

- **6:00 y 18:00:** trae ofertas de las 21 empresas, de las alertas de Gmail y las pasantías remotas internacionales de Himalayas, y evalúa con Gemini las nuevas.
- **6:05:** consulta JSearch (una vez al día); esas ofertas se evalúan en la corrida de las 18:00.

Si la computadora estuvo apagada a esa hora, esa corrida se pierde: haz una a mano (abajo).

## 1. Revisar que la app esté encendida

```bash
docker compose ps
```

Tienen que aparecer `db`, `web` y `worker` con estado **Up**. Si no aparece nada o dicen **Exited**:

```bash
docker compose up -d
```

Espera un minuto: la base de datos tarda en arrancar.

## 2. Traer ofertas y evaluarlas a mano

```bash
docker compose exec worker python -m moneyplease ingest
docker compose exec worker python -m moneyplease match
```

- `ingest` imprime una línea por fuente: `ok=True` es que funcionó, `nuevas=` cuántas ofertas nuevas trajo. `gmail` son tus alertas de LinkedIn.
- `match` termina con `embebidas=… candidatas=… evaluadas=… fallidas=…`. *Candidatas* son las nuevas que pasaron los filtros de tu perfil (Costa Rica, provincias, modalidad); solo esas van a Gemini.

## 3. Ver los resultados

```bash
docker compose exec worker python -m moneyplease recientes
docker compose exec worker python -m moneyplease top
```

- `recientes` lista todo lo evaluado en las últimas 24 horas, de mayor a menor puntaje, con el enlace. Para otro periodo: `recientes --horas 6`.
- `top` muestra tus 10 mejores ofertas activas con fortalezas, brechas y resumen. Variantes: `top --n 20`, `top --fit practica`, `top --min-score 80`.

O abre el dashboard: **http://localhost:8000** en la computadora, o **https://acid.tailad3a63.ts.net** en el teléfono (con Tailscale conectado).

## Problemas comunes

| Qué ves | Qué pasa | Qué hacer |
|---|---|---|
| `connection timeout expired` | La base de datos no está encendida o acaba de arrancar | `docker compose up -d`, esperar un minuto y repetir |
| `docker compose ps` no muestra nada | Los contenedores se apagaron (por ejemplo, al reiniciar la computadora) | `docker compose up -d` |
| Docker Desktop no abre | Archivo trabado del *Secrets Engine* | Cerrar Docker, renombrar `%LOCALAPPDATA%\docker-secrets-engine` a `docker-secrets-engine.old` y abrir Docker de nuevo |
| `gmail ok=True traidas=0` siempre | No llegan alertas a la etiqueta | Revisar los filtros de reenvío de Gmail (abajo) |
| `gmail ok=False` con error de token | El permiso de Gmail venció o se revocó | `cd backend` y `uv run python -m moneyplease gmail-auth` |
| `cuota agotada` en `match` | Se acabó la cuota gratuita diaria de Gemini | Esperar al día siguiente; lo pendiente se evalúa solo |
| El teléfono no abre la app | La computadora está apagada, Docker cerrado o Tailscale desconectado en alguno de los dos | Revisar los tres |

> ⚠️ **Nunca uses "Reset to factory defaults" en Docker Desktop ni `docker compose down -v`**: borran la base de datos con todas tus ofertas, evaluaciones y postulaciones.

## Alertas de LinkedIn por correo

- LinkedIn manda las alertas a **alexfallas1100@gmail.com**, que las reenvía (filtro) a **money.please.alexander@gmail.com**.
- En money.please, un filtro les pone la etiqueta **`Empleo/Alertas`**, que es la única que lee la app.
- Los filtros deben incluir estos remitentes: `jobalerts-noreply@linkedin.com OR jobs-listings@linkedin.com OR jobs-noreply@linkedin.com OR indeed.com`.
- Las alertas que reenvíes a mano no sirven: la app reconoce al remitente original, y el reenvío manual lo cambia por ti.

## Cambiar lo que se evalúa

En el dashboard, **Perfil**: modalidades, provincias, provincias para ofertas sin modalidad ("Sin modalidad indicada"), títulos y palabras a excluir. Guardar crea una versión nueva del perfil.
