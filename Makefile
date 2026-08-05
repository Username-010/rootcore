# PlantPilot developer commands
# Requires: Python 3.12+, Node 20+, Docker or Podman + docker-compose

export PATH := $(HOME)/.local/node/bin:$(HOME)/.local/bin:$(PATH)

COMPOSE ?= docker-compose
# Prefer Docker socket; fall back to Podman user socket
DOCKER_HOST_PODMAN := unix://$(XDG_RUNTIME_DIR)/podman/podman.sock

.PHONY: help env install backend-install frontend-install \
	db-up db-down dev-up dev-down migrate api web test test-api test-web lint \
	build podman-socket start stop restart status

help:
	@echo "PlantPilot make targets"
	@echo "  make start            ONE command: DB + migrate + API + web"
	@echo "  make stop             Stop API + web (DB keeps running)"
	@echo "  make stop-all         Stop API + web + Postgres"
	@echo "  make restart          Restart everything"
	@echo "  make status           Show running services"
	@echo "  make install          Install backend + frontend deps"
	@echo "  make db-up            Start Postgres only"
	@echo "  make migrate          Run Alembic migrations"
	@echo "  make api              Run API in foreground"
	@echo "  make web              Run Vite in foreground"
	@echo "  make test             Run backend tests"
	@echo "  make build            Build production Compose images"

start:
	@chmod +x scripts/plantpilot
	./scripts/plantpilot start

stop:
	@chmod +x scripts/plantpilot
	./scripts/plantpilot stop

stop-all:
	@chmod +x scripts/plantpilot
	./scripts/plantpilot stop --all

restart:
	@chmod +x scripts/plantpilot
	./scripts/plantpilot restart

status:
	@chmod +x scripts/plantpilot
	./scripts/plantpilot status

env:
	@test -f .env || cp .env.example .env
	@echo ".env ready"

podman-socket:
	systemctl --user enable --now podman.socket
	@echo "Podman socket: $(DOCKER_HOST_PODMAN)"
	@echo "Use: export DOCKER_HOST=$(DOCKER_HOST_PODMAN)"

install: backend-install frontend-install

backend-install:
	cd backend && uv sync --all-extras

frontend-install:
	cd frontend && npm install

db-up: env
	@if [ -S "$(XDG_RUNTIME_DIR)/podman/podman.sock" ] || systemctl --user is-active podman.socket >/dev/null 2>&1; then \
		DOCKER_HOST=$(DOCKER_HOST_PODMAN) $(COMPOSE) up -d db; \
	else \
		$(COMPOSE) up -d db; \
	fi

db-down:
	@if [ -S "$(XDG_RUNTIME_DIR)/podman/podman.sock" ]; then \
		DOCKER_HOST=$(DOCKER_HOST_PODMAN) $(COMPOSE) down; \
	else \
		$(COMPOSE) down; \
	fi

dev-up: env
	@if [ -S "$(XDG_RUNTIME_DIR)/podman/podman.sock" ] || systemctl --user start podman.socket 2>/dev/null; then \
		DOCKER_HOST=$(DOCKER_HOST_PODMAN) $(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up -d --build; \
	else \
		$(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up -d --build; \
	fi

dev-down:
	@if [ -S "$(XDG_RUNTIME_DIR)/podman/podman.sock" ]; then \
		DOCKER_HOST=$(DOCKER_HOST_PODMAN) $(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml down; \
	else \
		$(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml down; \
	fi

migrate: env
	cd backend && uv run alembic upgrade head

api: env
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web:
	cd frontend && npm run dev

test: test-api

test-api:
	cd backend && uv run pytest -q

test-web:
	cd frontend && npm test

lint:
	cd backend && uv run ruff check app tests
	cd frontend && npm run lint

build: env
	@if [ -S "$(XDG_RUNTIME_DIR)/podman/podman.sock" ]; then \
		DOCKER_HOST=$(DOCKER_HOST_PODMAN) $(COMPOSE) build; \
	else \
		$(COMPOSE) build; \
	fi
