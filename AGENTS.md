# AGENTS

NBA analytics monorepo: scrape → Postgres → dbt → API / MCP / Cube → Next.js.

Prefer [docs/](docs/) and root [README.md](README.md) over inventing behavior.

## Service map

- `services/scraper` — NBA Stats API + Basketball-Reference contracts / current injuries → schema `source`. Optional `SLACK_WEBHOOK_URL`: one Incoming Webhook per failed sync (`pipeline` / `scrape-daily` / `scrape-all` / `refresh`), not per step; unset/empty skips HTTP. Optional `ODDS_API_KEY`: The Odds API upcoming slate (`scrape-odds` / daily); unset/empty skips odds HTTP. Optional `REDDIT_*`: everyday r/nba posts and top comments whenever the pipeline is enabled (not behind `season_active`); unset/empty skips reddit HTTP. Season-active daily: slate, Finals logs, those games’ PBP, standings, injuries, remaining-year contracts, odds-if-keyed. `scrape-all` with no `--seasons` is the current season only; pass `--seasons` for a later backfill
- `services/migrate` — Alembic for **source** tables only (`make db-migrate`); shared by all services
- `services/dbt` — dbt `source` → `silver` (staging/intermediate) + `gold` (marts)
- `services/ml` — Elo pregame WP job (Python **3.14**, profile `tools`); reads gold Regular Season Finals + schedule, writes `source.game_predictions`
- `services/api` — FastAPI `/api/v1/*` over `gold`
- `services/frontend` — Next.js; `NEXT_PUBLIC_API_URL` → API
- `services/mcp` — FastMCP tools over Cube (named wrappers + `query_cube`; no gold SQL)
- `services/cube` — Cube YAML over gold; **required** for local Ask/MCP (`make up` / Tilt). Off on the 12GB prod overlay
- Schemas: `source` (ingest + pipeline gate), `silver` (dbt staging), `gold` (dims/facts)
- Init: `db/init.sql` creates those schemas empty; Alembic fills `source`

## Python / imports

- Pins: api, scraper, mcp, cube, migrate, ml → **3.14**
- Pins: dbt → **3.13**
- Pytest: `pythonpath = ["src"]`
- Use absolute imports from `src/`
- Env: copy `.env.example` → `.env`
- Keep `DATABASE_URL` in sync
- Docker: target `runtime` (prod) or `development` (Tilt)

## Commands

- `make up` / `make down` — Tilt local stack; `down` / `tilt down` also remove the `nba` buildx builder
- `make build` — native-arch runtime images (host amd64 or arm64; all services)
- `make build-multiarch` — linux/amd64 + linux/arm64 via buildx (`docker-bake.hcl`)
- `make test` — api, scraper, mcp, cube, ml, frontend unit, dbt e2e
- `make test-api|scraper|mcp|cube|ml|frontend|frontend-e2e|dbt|migrate`
- `make test-migrate-unit` — Alembic unit only (`-m "not integration"`; what CI runs)
- `make quality` — `pre-commit run --all-files` (runs `npm ci` in `services/frontend` if prettier is missing)
- `make db-migrate` / `make migrate` — Alembic `upgrade head` (source schema)
- `make scrape` — `pipeline run-once` honoring `source.scrape_pipeline` (`FORCE=1` → `--force`)
- `make dbt` — dbt `deps` / `seed` / `run` / `test`
- `make ml` — Elo `score` then `dbt run --select stg_game_predictions+`
- `make refresh` — scrape then dbt then ml (`refresh-daily` alias; `refresh-daily-once` is `FORCE=1`)
- `make prod-config` / `prod-up` / `prod-migrate` — Caddy overlay (`docker-compose.prod.yml`); not Tilt
- `make prod-deploy` — server: ff-only pull `main`, then `prod-release` (never `compose down -v`)
- `make prod-release` — images, migrate, up, caddy reload, `prod-health`, `prod-prune`. `IMAGE_PREFIX` set → `prod-pull` (GHCR); empty → `prod-build` (on-box)
- `make prod-release IMAGE_TAG=<sha>` — rollback to a previously pushed image; does not rebuild and does not touch Alembic
- `make sync` — refresh uv locks per Python pin
- Compose profiles: `tools` (scraper/dbt/ml); MCP and Cube are on the default local stack (not a profile)
- Docker: no `platform: linux/amd64` pin; bases are official multi-arch manifests

## Testing

- Python: pytest + coverage (fail under 90%); mostly unit
- Prefer real DB integration (e.g. Testcontainers) when adding DB tests
- dbt: no Python unit tests
- `make test-dbt` runs Alembic then seeds via `docker-compose.e2e.yml` + `services/dbt/e2e/run.sh`
- Frontend: Vitest coverage; Playwright e2e separately
- GitHub Actions (`.github/workflows/ci.yml`) runs `make quality` (pre-commit), `make test-frontend`, and `make test-api|scraper|mcp|cube|ml|migrate-unit` on PR/`main`. Not dbt e2e, Playwright, or Testcontainers. Then `images` bakes the `prod` bake group for `linux/arm64` on `ubuntu-24.04-arm` and pushes `:<sha>` + `:latest` to GHCR, and `deploy` SSHs `make prod-deploy IMAGE_PREFIX=… IMAGE_TAG=<sha>`. Both run on push to `main` or `workflow_dispatch` only when `ENABLE_OCI_DEPLOY=true` (never on pull_request). Public host is `baseline.jyablonski.dev`.

## Docs

- [docs/data.md](docs/data.md) — ingest / dbt / Cube
- [docs/frontend.md](docs/frontend.md) — Next.js ↔ API
- [docs/mcp-and-ai.md](docs/mcp-and-ai.md) — MCP tools; rule-based `/api/v1/query`; planned LLM
- [docs/plans/oci-caddy-hosting.md](docs/plans/oci-caddy-hosting.md) — Caddy/CI files in-repo; public host not live
- [docs/plans/ml-win-predictions.md](docs/plans/ml-win-predictions.md) — in progress: Elo v0 + upcoming games + BRef injuries + Odds API ingest; logit / Courtline / `/ask` still planned
- [docs/plans/ask-llm-providers.md](docs/plans/ask-llm-providers.md) — planned: Cursor Pro via MCP (not Courtline `/ask`); local OpenAI-compatible for browser LLM; hosted keys opt-in
- `GET /api/v1/status` is **current**: `last_scraped_at` from `source.scrape_pipeline.last_success_at` plus warehouse coverage counts. Do not surface `GET /health` in the UI.
- `POST /api/v1/query` and `/ask` are **current**. Default backend is **rules** (`NLP_BACKEND=rules`): B2B, season averages, compare, arena-city record, salary/payroll, standings — each family is a Cube query. Unrecognized questions return a capability message, not HTTP 501. `NLP_BACKEND=llm` is an opt-in adapter (Cube meta + `query_cube` / named Cube tools, needs `NLP_LLM_API_KEY`); it is not the public default and does not run SQL. MCP `query_cube` is Cube query JSON only. Cube down → clear Ask/MCP error; no gold SQL fallback. Prod 12GB overlay keeps Cube off, so MCP starts but its Cube-backed calls fail clearly.

## Conventions

- Do not commit unless the user asks
- Do not invent features; label planned vs current
- dbt owns SQL + YAML tests, not Python unit tests
- Scraper / dbt / ml → profile `tools`; MCP is on the default stack
- Frontend agent notes: `services/frontend/AGENTS.md`
- dbt agent notes: `services/dbt/AGENTS.md`
- Markdown: never impose a line-length / wrap limit. Do not hard-wrap prose in `.md` files. Do not reflow paragraphs to 80 (or any) columns. Coding agents must not “fix” wrapping by adding mid-paragraph newlines.
