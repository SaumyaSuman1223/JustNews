.DEFAULT_GOAL := help

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up: ## start local stack
	@echo "TODO(session 0.2): docker compose up -d"

down: ## stop local stack
	@echo "TODO(session 0.2): docker compose down"

logs: ## tail service logs
	@echo "TODO(session 0.2)"

test: ## run all tests
	@echo "TODO(session 0.4): uv run pytest -q && pnpm test"

lint: ## lint + typecheck everything
	@echo "TODO(session 0.4): uv run ruff check . && pnpm lint"

migrate: ## apply database migrations
	@echo "TODO(session 3.1): uv run alembic upgrade head"

seed: ## load development fixtures
	@echo "TODO(session 3.4)"

.PHONY: help up down logs test lint migrate seed
