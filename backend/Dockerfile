# Contexto de build: la raíz del repo (docker-compose usa context: .).

# 1) Frontend: compila el dashboard de React.
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2) Backend: paquete Python (worker y API) más el frontend compilado en /app/static.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_CACHE=1 PATH="/app/.venv/bin:$PATH" TZ=America/Costa_Rica
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ .
RUN uv sync --frozen --no-dev
COPY --from=frontend /app/frontend/dist /app/static
