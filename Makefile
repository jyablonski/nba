.PHONY: up down stop logs \
	test test-api test-scraper test-mcp test-cube test-ml test-frontend test-frontend-e2e test-dbt \
	test-migrate test-migrate-unit test-api-integration test-scraper-integration test-mcp-integration test-integration \
	build build-multiarch ensure-buildx-builder remove-buildx-builder sync db-migrate migrate \
	pipeline-status pipeline-enable pipeline-disable scrape dbt ml refresh \
	refresh-daily refresh-daily-once \
	prod-config prod-up prod-migrate prod-deploy prod-release prod-build prod-pull \
	prod-health prod-prune quality

COMPOSE ?= docker compose
TILT ?= tilt
DOCKER_TARGET ?= runtime
# Same compose project as Tilt (directory name, usually nba).
COMPOSE_PROJECT_NAME ?= $(notdir $(CURDIR))
export COMPOSE_PROJECT_NAME
# One-shots must not reconcile depends_on postgres (recreates Tilt's container).
COMPOSE_RUN_TOOLS = $(COMPOSE) --profile tools run --rm --no-deps
COMPOSE_PROD = $(COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml
# Host-native `make build` leaves this unset. Multi-arch bake uses both.
PLATFORMS ?= linux/amd64,linux/arm64
BUILDX_BUILDER ?= nba
# Public origin. Caddyfile hardcodes the same host (Caddy needs it for ACME).
PUBLIC_HOST ?= baseline.jyablonski.dev
PUBLIC_URL ?= https://$(PUBLIC_HOST)
export PUBLIC_URL
# Registry coordinates for bake tags and the prod overlay's `image:` refs.
# Empty IMAGE_PREFIX = local images (`nba-api:latest`) built on this machine;
# set it (e.g. ghcr.io/jyablonski/) to deploy prebuilt images instead.
IMAGE_PREFIX ?=
IMAGE_TAG ?= latest
export IMAGE_PREFIX
export IMAGE_TAG

up: ## Start the stack with Tilt (hot reload)
	DOCKER_TARGET=development $(TILT) up

prod-config: ## Validate prod overlay
	$(COMPOSE_PROD) config

prod-up: ## Runtime images + caddy (needs DOCKER_TARGET=runtime)
	DOCKER_TARGET=runtime $(COMPOSE_PROD) up -d postgres api frontend caddy

prod-migrate: ## Alembic upgrade head via prod overlay (one-shot; does not recreate postgres)
	DOCKER_TARGET=runtime $(COMPOSE_PROD) run --rm --no-deps migrate alembic upgrade head

# Registry deploys pull prebuilt images; without IMAGE_PREFIX we build on the box.
# Command-line overrides reach the sub-make in prod-deploy through MAKEFLAGS.
ifeq ($(strip $(IMAGE_PREFIX)),)
PROD_IMAGES := prod-build
else
PROD_IMAGES := prod-pull
endif

# Server entrypoint for CI SSH (`cd /opt/nba && make prod-deploy`).
# Pull first, then re-invoke make so a newly pulled Makefile is used.
# Never `compose down -v` (wipes pgdata).
prod-deploy: ## Server: ff-only pull main, then prod-release
	git fetch origin main
	git checkout main
	git pull --ff-only origin main
	$(MAKE) prod-release

prod-release: $(PROD_IMAGES) ## Images, migrate, up, caddy reload, health gate, prune
	DOCKER_TARGET=runtime $(COMPOSE_PROD) up -d postgres --wait
	$(MAKE) prod-migrate
	$(MAKE) prod-up
	-$(COMPOSE_PROD) exec -T caddy caddy reload --config /etc/caddy/Caddyfile
	$(MAKE) prod-health
	$(MAKE) prod-prune

# `--parallel 1` keeps the Next.js build (2-4GB peak) from racing the others.
prod-build: ## Build runtime images on this machine (on-box deploy path)
	DOCKER_TARGET=runtime $(COMPOSE_PROD) build --parallel 1 api frontend migrate

prod-pull: ## Pull prebuilt runtime images (registry deploy path; needs IMAGE_PREFIX)
	$(COMPOSE_PROD) pull postgres caddy migrate api frontend

# Probe from inside the compose network: a deploy must not depend on public DNS
# or on Caddy already holding a cert. Caddy's alpine image ships busybox wget.
define wait_ok
for i in $$(seq 1 20); do \
	if $(COMPOSE_PROD) exec -T caddy wget -q -O /dev/null -T 3 "$(1)"; then exit 0; fi; \
	sleep 3; \
done; \
echo "prod-health: $(2) never answered at $(1)" >&2; exit 1
endef

prod-health: ## Fail the deploy if api or frontend did not come back up
	@$(call wait_ok,http://api:8000/health,api)
	@$(call wait_ok,http://frontend:3000/,frontend)

# Dangling layers only. `-a` would delete the previous release's images and
# with them the fast rollback path.
prod-prune: ## Drop dangling layers left behind by the last build
	docker image prune -f

down: ## Stop Tilt and tear down compose resources (also drops the nba buildx builder)
	-$(TILT) down
	$(COMPOSE) --profile tools --profile cube --profile cron down --remove-orphans
	-./scripts/remove-buildx-builder.sh

stop: down

logs: ## Tail compose logs
	$(COMPOSE) logs -f

# Compose has no `platform:` pin — Docker builds for this machine's CPU.
# Include tools so `make build` covers the full image set (not only
# api/frontend/cube). refresh-daily rebuilds nba-scraper and nba-dbt.
# `--profile cube` is kept for older compose files that still profile Cube.
build: ## Build runtime images for this machine's CPU (amd64 or arm64)
	DOCKER_TARGET=$(DOCKER_TARGET) $(COMPOSE) --profile tools --profile cube build

# docker-container driver can emit a multi-arch manifest; classic `docker load`
# cannot. Without PUSH=1 the images stay in the buildx builder cache.
# Qemu: Docker Desktop usually has it; Linux may need:
#   docker run --privileged --rm tonistiigi/binfmt --install amd64,arm64
build-multiarch: ensure-buildx-builder ## Build linux/amd64 and linux/arm64 (buildx)
ifeq ($(PUSH),1)
ifeq ($(IMAGE_PREFIX),)
	$(error PUSH=1 requires IMAGE_PREFIX, e.g. IMAGE_PREFIX=ghcr.io/org/)
endif
endif
	DOCKER_TARGET=$(DOCKER_TARGET) \
	PLATFORMS=$(PLATFORMS) \
	IMAGE_PREFIX=$(IMAGE_PREFIX) \
	IMAGE_TAG=$(IMAGE_TAG) \
	NEXT_PUBLIC_API_URL=$(or $(NEXT_PUBLIC_API_URL),http://localhost:8000) \
	docker buildx bake --builder $(BUILDX_BUILDER) --file docker-bake.hcl \
		$(if $(filter 1,$(PUSH)),--push,)

ensure-buildx-builder:
	@if ! docker buildx inspect $(BUILDX_BUILDER) >/dev/null 2>&1; then \
		echo "Creating buildx builder $(BUILDX_BUILDER) (docker-container driver)"; \
		docker buildx create --name $(BUILDX_BUILDER) --driver docker-container --bootstrap; \
	fi

remove-buildx-builder: ## Remove the docker-container buildx builder (BuildKit) if it exists
	./scripts/remove-buildx-builder.sh

sync: ## Refresh uv locks for all Python services
	uv lock --python 3.14
	cd services/migrate && uv lock --python 3.14
	cd services/api && uv lock --python 3.14
	cd services/scraper && uv lock --python 3.14
	cd services/mcp && uv lock --python 3.14
	cd services/cube && uv lock --python 3.14
	cd services/ml && uv lock --python 3.14
	cd services/dbt && uv lock --python 3.13

db-migrate migrate: ## Apply Alembic source-schema revisions (does not recreate postgres)
	$(COMPOSE) run --rm --no-deps migrate alembic upgrade head

pipeline-status: ## Show source.scrape_pipeline gate flags (enabled, season_active)
	$(COMPOSE_RUN_TOOLS) scraper python -m main pipeline status

pipeline-enable: ## Enable daily scrape gate (season_active; reddit always runs when enabled)
	$(COMPOSE_RUN_TOOLS) scraper python -m main pipeline enable \
		--season-active --reason "Enabled via make pipeline-enable" \
		$(PIPELINE_FLAGS)

pipeline-disable: ## Disable scrape gate (safe default / off-season)
	$(COMPOSE_RUN_TOOLS) scraper python -m main pipeline disable

scrape: ## pipeline scrape honoring source.scrape_pipeline (does not run dbt)
	$(COMPOSE_RUN_TOOLS) scraper python -m main pipeline run-once $(if $(filter 1,$(FORCE)),--force,)

dbt: ## dbt deps + seed + run + test (does not scrape)
	$(COMPOSE_RUN_TOOLS) dbt sh -c \
		'dbt deps --profiles-dir . && dbt seed --profiles-dir . && dbt run --profiles-dir . && dbt test --profiles-dir .'

ml: ## Elo score then copy source.game_predictions into gold
	$(COMPOSE_RUN_TOOLS) ml python -m main score
	$(COMPOSE_RUN_TOOLS) dbt sh -c \
		'dbt deps --profiles-dir . && dbt run --profiles-dir . --select stg_game_predictions+'

refresh: ## scrape then dbt then ml; bind-mounts host files; does not recreate postgres
	FORCE=0 ./scripts/refresh-daily.sh

refresh-daily: refresh ## alias for refresh

refresh-daily-once: ## Force one scrape→dbt→ml cycle; bind-mounts host files; does not recreate postgres
	FORCE=1 ./scripts/refresh-daily.sh

test: test-api test-scraper test-mcp test-cube test-ml test-frontend test-dbt ## Run all automated suites (unit + dbt e2e)

test-migrate: ## Alembic unit tests + upgrade head on throwaway Postgres
	cd services/migrate && uv sync --group dev && uv run pytest

test-migrate-unit: ## Alembic unit tests only (no Testcontainers; CI PR path)
	cd services/migrate && uv sync --group dev && uv run pytest -m "not integration"

quality: ## Repo pre-commit hooks on all files (ruff --fix fails CI if it leaves a dirty tree)
	@if [ ! -x services/frontend/node_modules/prettier/bin/prettier.cjs ]; then \
		cd services/frontend && npm ci; \
	fi
	uv run --group local pre-commit run --all-files

test-api: ## API unit tests with coverage (excludes integration)
	cd services/api && uv sync --group dev && uv run pytest

test-scraper: ## Scraper unit tests with coverage (excludes integration)
	cd services/scraper && uv sync --group dev && uv run pytest

test-mcp: ## MCP unit tests with coverage (excludes integration)
	cd services/mcp && uv sync --group dev && uv run pytest

test-cube: ## Cube schema unit tests with coverage
	cd services/cube && uv sync --group dev && uv run pytest

test-ml: ## ML Elo unit tests with coverage
	cd services/ml && uv sync --group dev && uv run pytest

test-frontend: ## Frontend unit tests with coverage
	cd services/frontend && npm install && npm run test:coverage

test-frontend-e2e: ## Frontend Playwright e2e
	cd services/frontend && npm install && npx playwright install chromium && CI=1 npm run test:e2e

test-api-integration: ## API Testcontainers Postgres
	cd services/api && uv sync --group dev && uv run pytest -m integration --cov-fail-under=0

test-scraper-integration: ## Scraper Testcontainers Postgres
	cd services/scraper && uv sync --group dev && uv run pytest -m integration --cov-fail-under=0

test-mcp-integration: ## MCP Testcontainers Postgres
	cd services/mcp && uv sync --group dev && uv run pytest -m integration --cov-fail-under=0

test-integration: test-migrate test-api-integration test-scraper-integration test-mcp-integration ## All Python integration suites

test-dbt: ## dbt e2e against a seeded ephemeral Postgres
	COMPOSE_PROJECT_NAME=nba-e2e $(COMPOSE) -p nba-e2e -f docker-compose.e2e.yml build migrate dbt
	COMPOSE_PROJECT_NAME=nba-e2e $(COMPOSE) -p nba-e2e -f docker-compose.e2e.yml up -d postgres --wait
	COMPOSE_PROJECT_NAME=nba-e2e $(COMPOSE) -p nba-e2e -f docker-compose.e2e.yml run --rm migrate
	COMPOSE_PROJECT_NAME=nba-e2e $(COMPOSE) -p nba-e2e -f docker-compose.e2e.yml run --rm \
		--entrypoint bash dbt e2e/run.sh
	COMPOSE_PROJECT_NAME=nba-e2e $(COMPOSE) -p nba-e2e -f docker-compose.e2e.yml down -v --remove-orphans
