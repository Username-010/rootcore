# syntax=docker/dockerfile:1
# Multi-stage production image: build SPA, run API, serve static.

FROM node:22-bookworm-slim AS frontend-build
WORKDIR /frontend
ENV npm_config_update_notifier=false \
    npm_config_fund=false \
    npm_config_audit=false
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN rm -rf node_modules && (npm ci || npm install) && npm run build && test -f dist/index.html

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MEDIA_ROOT=/data/media \
    STATIC_DIR=/app/static
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 rootcore
COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
RUN pip install --upgrade pip && pip install .
COPY --from=frontend-build /frontend/dist /app/static
RUN mkdir -p /data/media && chown -R rootcore:rootcore /app /data
USER rootcore
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
