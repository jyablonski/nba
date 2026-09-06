# Testing and CI

How this repo is tested, and what GitHub actually runs. Command aliases also live in the root [README](../README.md) and [AGENTS.md](../AGENTS.md). dbt quality is SQL/YAML, not pytest — see [data.md](data.md).

## Purpose

Stop guessing which `make test-*` is unit, Docker, or a no-op on CI.

## Layers (current)

| Layer              | How                                                                                           | Coverage / notes                                                                                                                                                                                                                                                      |
| ------------------ | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Python unit        | `make test-api` / `test-scraper` / `test-mcp` / `test-cube` / `test-ml` / `test-migrate-unit` | pytest default is `-m "not integration"`. `--cov-fail-under=90` on api, scraper, mcp, cube, ml.                                                                                                                                                                       |
| Frontend unit      | `make test-frontend`                                                                          | Vitest + coverage (`npm run test:coverage`).                                                                                                                                                                                                                          |
| Alembic + DB       | `make test-migrate`                                                                           | Unit **and** upgrade on throwaway Postgres (Testcontainers).                                                                                                                                                                                                          |
| Python integration | `make test-api-integration` (and scraper) or `make test-integration`                          | Testcontainers Postgres. Need a Docker socket. Apply `db/init.sql` + Alembic. API seeds gold from `db/analytics_integration*.sql`. MCP unit tests mock Cube (no live Cube). Auto-skip if Docker is missing. `--cov-fail-under=0` so the 90% unit gate is not applied. |
| dbt e2e            | `make test-dbt`                                                                               | `docker-compose.e2e.yml` + `services/dbt/e2e/run.sh`. Runs migrate first, then seed/run/test, then `down -v`. Project name `nba-e2e`.                                                                                                                                 |
| Playwright         | `make test-frontend-e2e`                                                                      | Separate from Vitest.                                                                                                                                                                                                                                                 |

`make test` is unit suites + frontend unit + dbt e2e. It is **not** Testcontainers and **not** Playwright.

Python services use `pythonpath = ["src"]` and absolute imports. Pins: 3.14 except dbt at 3.13.

## Quality

`make quality` runs `pre-commit run --all-files` (group `local`). If frontend Prettier is missing it runs `npm ci` in `services/frontend` first.

Hooks: ruff check `--fix` + format, trailing whitespace / EOF / yaml / toml / debug statements, Prettier (js/ts/css/json/markdown/yaml), frontend eslint `--max-warnings=0`. `ruff --fix` that leaves a dirty tree fails CI — commit the format.

## GitHub Actions (`.github/workflows/ci.yml`)

On `pull_request`, push to `main`, and `workflow_dispatch`:

1. `quality` — `make quality`
2. `frontend` — `make test-frontend`
3. `python` matrix — `make test-api` / `test-scraper` / `test-mcp` / `test-cube` / `test-ml` / `test-migrate-unit` (`fail-fast: false`)

**Not on CI:** `make test-dbt`, Playwright, Testcontainers / `make test-integration` / `make test-migrate`.

`deploy` SSHs `make prod-deploy` only when `ENABLE_OCI_DEPLOY=true` and the event is **not** `pull_request`. See [plans/oci-caddy-hosting.md](plans/oci-caddy-hosting.md).

## Local habits

Prefer real DB integration when adding repository SQL. Do not add Python unit tests under `services/dbt`. Do not run `make test-dbt` on the production VM (`down -v` wipes that compose project’s volume — still not something to point at prod `pgdata`).
