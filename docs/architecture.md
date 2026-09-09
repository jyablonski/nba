# Architecture

Who talks to whom in this monorepo. The root [README](../README.md) has the one-box mermaid and quick start. Ingest and marts live in [data.md](data.md). Cube's semantic model and runtime are in [cube.md](cube.md). Courtline screens live in [frontend.md](frontend.md). MCP tools live in [mcp-and-ai.md](mcp-and-ai.md). Agent pins and Make aliases stay in [AGENTS.md](../AGENTS.md).

## Purpose

Keep service boundaries honest: the browser never opens Postgres, scrape jobs never serve HTTP, and gold is the only product read path.

## Runtime groups

Compose default (`make up` / Tilt, `DOCKER_TARGET=development`): **postgres**, one-shot **migrate**, **cube**, **api**, **frontend**, **mcp**.

| Profile | Services                                    | Always-on?                                                         |
| ------- | ------------------------------------------- | ------------------------------------------------------------------ |
| (none)  | postgres, migrate, cube, api, frontend, mcp | yes (migrate exits)                                                |
| `tools` | scraper, dbt, ml                            | no — `compose run`                                                 |
| `cron`  | `refresh-daily` container                   | no; scrape-only entrypoint — prefer [operations.md](operations.md) |

Production overlay (`docker-compose.prod.yml`) is postgres + api + frontend + Cube + MCP + Caddy. Cube is internal to the Compose network and port 4000 is not published. MCP serves authenticated Streamable HTTP on host port 8001. Tilt and profile `cron` stay off. Ask/MCP fail clearly if Cube or `CUBE_API_URL` is unavailable. Go-live still needs a VM; see [plans/oci-caddy-hosting.md](plans/oci-caddy-hosting.md).

Images use target `runtime` or `development`. There is no Compose `platform:` pin.

## Schemas and writers

`db/init.sql` creates empty `source`, `silver`, and `gold`. Alembic in `services/migrate` owns **source** DDL (`make db-migrate`). dbt in `services/dbt` owns silver/gold. The scraper does not bootstrap tables.

| Writer  | Schema                    | Notes                                                                                                                                                          |
| ------- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| scraper | `source`                  | Basketball-Reference schedules, rosters, box scores, standings, contracts, injuries, and play-by-play; optional Odds / Reddit. CLI help only on compose start. |
| ml      | `source.game_predictions` | Elo v0 after gold Finals + schedule exist. See [ml.md](ml.md).                                                                                                 |
| dbt     | `silver`, `gold`          | Reads `source`. Downstream never queries `source` for product.                                                                                                 |

API REST reads **gold**. Ask and MCP read gold only through Cube (`/load`, `/meta`). Frontend does not call Cube.

## API shape (`services/api`)

FastAPI `/api/v1/*` over gold. Layers:

- `routers/` — HTTP
- `repositories/` — session + row mapping
- `queries/` — SQL constants (`text()`), not a second ORM
- `schemas/` — Pydantic responses
- `cube/` — Cube REST client + named Ask operations
- `services/nlp/` — `/ask` backends; see [ask.md](ask.md)

Current routes: players (list, detail, game-log, season-stats, back-to-backs, compare, compare/head-to-head), teams (list, detail, games, record), games (recent + `/api/v1/seasons`), standings, `GET /api/v1/status`, `POST /api/v1/query`. `GET /health` is liveness only — do not show it in the UI. There is **no** public predictions endpoint. Head-to-head is gold player game logs on the same `game_id` with opposite `team_id` (not teammates).

CORS allows `http://localhost:3000`. The public host is same-origin via Caddy (`/api/*`).

## Who the frontend talks to

Courtline (`services/frontend`) calls only `${NEXT_PUBLIC_API_URL}/api/v1/...`. It does not use MCP, Cube, or SQL. `NEXT_PUBLIC_API_URL` is a **build-time** ARG. `/ask` stays `POST /api/v1/query`.

## Planned (not current)

Public predictions API, Courtline win-prob badge, Courtline Social tab ([plans/social-tab.md](plans/social-tab.md)), always-on scraper/dbt/ml on the 12GB VM.
