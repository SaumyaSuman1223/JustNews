.DEFAULT_GOAL := help
SHELL := /bin/bash

# Docker Compose is the primary local stack because it matches deployment.
# scripts/devdb.py is the fallback for machines without a Docker daemon
# (WSL without Docker Desktop integration, for instance) - it runs a real
# PostgreSQL with pgvector out of the pgserver wheel.
COMPOSE := docker compose

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# --- local stack --------------------------------------------------------

up: ## start the full local stack (docker)
	$(COMPOSE) up -d --build db redis api web
	@echo "api  http://localhost:8000/docs"
	@echo "web  http://localhost:3000"

down: ## stop the local stack, keeping data
	$(COMPOSE) down

clean: ## stop the local stack and delete its data
	$(COMPOSE) down -v

logs: ## tail service logs
	$(COMPOSE) logs -f --tail=100

db-up: ## start postgres without docker (fallback)
	uv run python scripts/devdb.py start

db-down: ## stop the docker-free postgres
	uv run python scripts/devdb.py stop

dev-api: ## run the api on the host with reload
	uv run uvicorn justnews_api.main:app --reload --port 8000

dev-web: ## run the web app on the host with reload
	pnpm --filter @justnews/web dev

# --- database -----------------------------------------------------------

migrate: ## apply database migrations
	cd apps/api && uv run alembic upgrade head

migration: ## generate a migration: make migration m="add x"
	cd apps/api && uv run alembic revision --autogenerate -m "$(m)"

seed: ## seed IPTC topics, editions, sources and feeds (idempotent)
	uv run justnews-ingest seed

# --- content ------------------------------------------------------------

ingest: ## one ingestion pass over every due feed
	uv run justnews-ingest run

prune: ## apply the retention window and report database size
	uv run justnews-ingest prune

stats: ## corpus size, language spread and quota usage
	uv run justnews-ingest stats

# --- quality ------------------------------------------------------------

test: ## run every test
	uv run pytest -q
	pnpm test --if-present

lint: ## lint and typecheck everything
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy packages/core/src apps/api/src apps/ingestion/src
	pnpm --filter @justnews/web lint
	pnpm --filter @justnews/web typecheck

format: ## autoformat
	uv run ruff check --fix .
	uv run ruff format .

build: ## production build of the web app
	pnpm --filter @justnews/web build

smoke: ## check every locale is served by a running web app
	bash scripts/smoke-web.sh

bootstrap: ## install every dependency from a cold clone
	uv sync
	pnpm install

.PHONY: help up down clean logs db-up db-down dev-api dev-web migrate migration \
        seed ingest prune stats test lint format build smoke bootstrap
