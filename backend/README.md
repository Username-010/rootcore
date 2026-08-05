# RootCore API

FastAPI backend for RootCore.

## Local development

```bash
# From repository root
cp .env.example .env
make backend-install
make db-up          # Postgres via Compose/Podman
make migrate
make api
```

API docs: http://localhost:8000/api/docs

## Tests

```bash
make test-api
```
