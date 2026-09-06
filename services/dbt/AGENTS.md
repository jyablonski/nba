# AGENTS — services/dbt

dbt project `nba_analytics` (profile `nba`):
`source` → staging / intermediate in schema `silver`, marts in schema `gold`.

See also root [AGENTS.md](../../AGENTS.md) and [docs/data.md](../../docs/data.md).

## SQL style (required)

- **Prefer CTEs over subqueries.** Use `with … as (…)` instead of
  derived tables in `from` / `join`, and instead of scalar
  `(select …)` in `select` / `where` when a CTE is clearer.
- **No short table aliases.** Reference full CTE or relation names
  (`players.player_id`, not `p.player_id`). Same table twice →
  two CTEs (e.g. `home_teams` / `away_teams`), not `as ht`.
- sqlfluff enforces the above where it can (see below); still follow
  the CTE / no-short-alias convention for cases rules miss
  (e.g. scalar subqueries).

## sqlfluff

- Config: **`pyproject.toml`** `[tool.sqlfluff.*]` only — do **not**
  add a `.sqlfluff` file. Keep `.sqlfluffignore`.
- Dialect `postgres`, templater `dbt` (needs reachable Postgres +
  `POSTGRES_*` env, same as dbt).
- Enabled tightenings:
  - `aliasing.forbid` (AL07) with `force_enable = true` — no table aliases
  - `aliasing.table` / `aliasing.column` — explicit `as` if an alias exists
  - `structure.subquery` (ST05) with `forbid_subquery_in = both` —
    no subqueries in `from` / `join` (use CTEs)
- Lint from this directory: `uv run sqlfluff lint models tests`

## Python / tooling

- Pin: **Python 3.13** (`requires-python = ">=3.13,<3.14"`)
- Quality: dbt SQL + YAML tests / singular tests — **no** pytest suite
- Local: `uv run dbt deps|run|test --profiles-dir .`
- Docker: `dbt deps` during image build; `dbt_packages` is copied
  into runtime so `--no-deps` compose runs do not need Hub access
- E2E: `make test-dbt` (repo root) → `docker-compose.e2e.yml` +
  `e2e/run.sh` (still runs `dbt deps` as a development-target fallback)

## Schemas

- Sources: schema `source` (`_staging__sources.yml`). Alembic owns this DDL.
- Staging + intermediate: `+schema: silver`
- Marts: `+schema: gold`
- `macros/generate_schema_name.sql` uses the custom schema as-is
  (avoids `gold_gold` concatenation)

## Layout

- `models/staging|intermediate|marts` + matching `*.yml`
- Singular tests: `tests/`
- Do not commit unless asked; avoid churning `uv.lock` unless deps change
