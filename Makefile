# Makefile — handy commands for developing and inspecting this project.
#
# Run `make help` (or just `make`) to see all available targets.
#
# Conventions: backend uses `uv`, frontend uses `npm`, stack runs via
# `docker compose`. DB credentials default to the values in
# backend/.env.example and can be overridden on the command line, e.g.
#   make db-shell POSTGRES_DB=mydb

# --- Config (override on the CLI: `make <target> VAR=value`) --------------
POSTGRES_USER     ?= postgres
POSTGRES_PASSWORD ?= postgres
POSTGRES_DB       ?= backend
COMPOSE           ?= docker compose
BACKEND_DIR       ?= backend
FRONTEND_DIR      ?= frontend

# psql invoked inside the running db container (no local psql required).
PSQL = $(COMPOSE) exec -T db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

.DEFAULT_GOAL := help

# --- Meta -----------------------------------------------------------------
.PHONY: help
help: ## Show this help
	@echo "Usage: make <target>"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Stack lifecycle ------------------------------------------------------
.PHONY: up
up: ## Build and start the full stack (frontend on :8080)
	$(COMPOSE) up --build -d

.PHONY: down
down: ## Stop and remove the stack (keeps the db volume)
	$(COMPOSE) down

.PHONY: db-up
db-up: ## Start only the Postgres service (for local backend dev)
	$(COMPOSE) up -d db

.PHONY: logs
logs: ## Tail logs for all services
	$(COMPOSE) logs -f

.PHONY: ps
ps: ## Show status of stack services
	$(COMPOSE) ps

.PHONY: status
status: ## Show Docker container status (state + health + ports)
	@$(COMPOSE) ps --format 'table {{.Name}}\t{{.Service}}\t{{.State}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null \
		|| $(COMPOSE) ps

# --- Migrations (Alembic, no ORM) -----------------------------------------
# Schema changes are Alembic revisions with hand-written raw SQL
# (op.execute). No ORM models, no --autogenerate. The backend also runs
# `alembic upgrade head` automatically on startup.
.PHONY: migrate
migrate: ## Apply pending migrations (needs db-up)
	cd $(BACKEND_DIR) && uv run alembic upgrade head

.PHONY: migrate-status
migrate-status: ## Show current revision and history (needs db-up)
	@echo "=== Current revision ==="
	@cd $(BACKEND_DIR) && uv run alembic current 2>/dev/null \
		|| echo "(cannot connect — is the db up? try 'make db-up')"
	@echo ""
	@echo "=== History ==="
	@cd $(BACKEND_DIR) && uv run alembic history

.PHONY: new-migration
new-migration: ## Scaffold a new revision: make new-migration name=add_user_status
	@test -n "$(name)" || { echo "Usage: make new-migration name=<description>"; exit 1; }
	cd $(BACKEND_DIR) && uv run alembic revision -m "$(name)"

.PHONY: migrate-downgrade
migrate-downgrade: ## Revert the last applied migration (dev only, needs db-up)
	cd $(BACKEND_DIR) && uv run alembic downgrade -1

# --- Backend --------------------------------------------------------------
.PHONY: backend-install
backend-install: ## Install backend dependencies (uv sync)
	cd $(BACKEND_DIR) && uv sync

.PHONY: backend-dev
backend-dev: ## Run the backend dev server with reload (needs db-up)
	cd $(BACKEND_DIR) && uv run uvicorn backend.app:app --reload

.PHONY: backend-test
backend-test: ## Run backend tests (needs Postgres running)
	cd $(BACKEND_DIR) && uv run pytest

.PHONY: backend-shell
backend-shell: ## Open a Python REPL with the backend package importable
	cd $(BACKEND_DIR) && uv run python

# --- Frontend -------------------------------------------------------------
.PHONY: frontend-install
frontend-install: ## Install frontend dependencies (npm ci)
	cd $(FRONTEND_DIR) && npm ci

.PHONY: frontend-dev
frontend-dev: ## Run the frontend dev server (Vite, proxies /api)
	cd $(FRONTEND_DIR) && npm run dev

.PHONY: frontend-build
frontend-build: ## Type-check and build the frontend
	cd $(FRONTEND_DIR) && npm run build

.PHONY: frontend-lint
frontend-lint: ## Lint the frontend (oxlint)
	cd $(FRONTEND_DIR) && npm run lint

# --- Database inspection --------------------------------------------------
.PHONY: db-shell
db-shell: ## Open an interactive psql shell in the db container
	$(COMPOSE) exec db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

.PHONY: db-tables
db-tables: ## List tables in the database
	@$(PSQL) -c "\dt"

.PHONY: db-users
db-users: ## Show rows in the users table
	@$(PSQL) -c "SELECT id, email, full_name, created_at FROM users ORDER BY created_at DESC;"

# --- Discovery (handy for agents) -----------------------------------------
.PHONY: tree
tree: ## Print the source tree (git-ignored artifacts excluded)
	@tree -a -I '.git|.venv|node_modules|__pycache__|.pytest_cache|dist' --dirsfirst 2>/dev/null \
		|| git ls-files

.PHONY: routes
routes: ## List backend HTTP routes
	@cd $(BACKEND_DIR) && uv run python -c "from backend.app import app; [print(f'{sorted(r.methods)}\t{r.path}') for r in app.routes if hasattr(r, 'methods')]"

.PHONY: info
info: ## Show project versions and toolchain info
	@echo "Node (.nvmrc):   $$(cat $(FRONTEND_DIR)/.nvmrc 2>/dev/null || echo '?')"
	@echo "Python:          $$(cat $(BACKEND_DIR)/.python-version 2>/dev/null || echo '?')"
	@echo "uv:              $$(uv --version 2>/dev/null || echo 'not installed')"
	@echo "node (local):    $$(node --version 2>/dev/null || echo 'not installed')"
	@echo "docker compose:  $$($(COMPOSE) version --short 2>/dev/null || echo 'not installed')"
