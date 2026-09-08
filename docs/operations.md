# Operations

Operator loop for a running stack: enable the gate, refresh gold, optional alerts. Scrape CLIs, marts, and Cube stay in [data.md](data.md). Elo score details are in [ml.md](ml.md). Hosting files vs go-live are in [plans/oci-caddy-hosting.md](plans/oci-caddy-hosting.md).

## Purpose

One place for “what do I run today” without restating every ingest command.

## Bring-up

```bash
cp .env.example .env
make up                 # Tilt: postgres, migrate, cube, api, frontend
make db-migrate         # after new Alembic revisions (exited migrate is not re-run)
```

Keep `DATABASE_URL` in sync with the Postgres settings. Wipe a stale volume only when you intend to: `docker compose down -v`. Cube is a RAM hog (~400–800 MB), so the production overlay gives it a 1 GB memory limit and keeps it internal to Compose; monitor VM memory when running refresh jobs alongside the always-on stack.

## Direct production database access

The production overlay publishes Postgres on `${POSTGRES_PORT:-5432}:5432` for direct tools such as DBeaver. The database remains on port `5432` inside the Compose network, so API, Cube, dbt, and migrations continue using `postgres:5432`. Set `POSTGRES_PORT` in the Oracle host's `.env` if the external port should differ, then run `make prod-up` or `make prod-release` to recreate the mapping.

Docker listens on all host interfaces for this mapping. To reach it from a local machine, allow inbound TCP on the selected port in the OCI VCN security list or network security group and any host firewall, then use the Oracle public IP or DNS name in DBeaver:

```text
Host: <oracle-public-ip-or-dns>
Port: 5432 (or POSTGRES_PORT)
Database: POSTGRES_DB
Username: POSTGRES_USER
Password: POSTGRES_PASSWORD
SSL: disabled unless separately configured
```

The credentials are the values in `/opt/nba/.env`; never paste them into the repository or logs. From the Oracle host, verify the listener with `sudo ss -ltnp | grep ':5432'` and test the OCI path from the workstation with `nc -vz <oracle-public-ip-or-dns> 5432`. Publishing the database port does not expose Cube or change the private Compose URLs.

Production MCP uses Streamable HTTP on `http://<oracle-public-ip-or-dns>:8001/mcp` and requires `Authorization: Bearer <MCP_API_TOKEN>`. Allow inbound TCP 8001 in the OCI VCN security list or network security group and any host firewall. The MCP service remains stdio for local development; `MCP_TRANSPORT=stdio` is the default in `.env`.

First load is manual (not `refresh-daily`): current-season / Courtline smoke is `scrape-all --active-only` (default ingest is the latest season) then dbt `seed`/`run`/`test` via profile `tools`. See [data.md](data.md). Omit `--active-only` only for full career-directory history. Pass `--seasons` for a later backfill. `scrape-all` skips Reddit unless `--with-reddit`. Injuries and odds are current snapshots, not the historical loop.

## Daily path (current)

`source.scrape_pipeline` is **disabled** by default (`enabled=false`, `season_active=false`). That singleton is the source of truth for which scrapes run. `pipeline_runs` still records whether reddit ran and its exit.

```bash
make pipeline-enable                    # enabled + season_active (NBA daily + reddit)
# reddit-only / off-season: make pipeline-enable PIPELINE_FLAGS=--no-season-active
make pipeline-status
make scrape                             # pipeline scrape only (FORCE=1 bypasses the gate)
make dbt                                # dbt deps + seed + run + test
make ml                                 # Elo score then gold copy
make refresh                            # scrape then dbt then ml (alias: refresh-daily)
make refresh-daily-once                 # FORCE=1 bypass for a manual test

# Oracle production jobs use the pulled GHCR images and the prod overlay:
IMAGE_PREFIX=ghcr.io/<owner>/ IMAGE_TAG=latest make prod-pipeline-enable
IMAGE_PREFIX=ghcr.io/<owner>/ IMAGE_TAG=latest make prod-refresh
IMAGE_PREFIX=ghcr.io/<owner>/ IMAGE_TAG=latest make prod-refresh-daily-once # FORCE=1 bypass for a manual test
```

`scripts/refresh-daily.sh` waits for an **existing** healthy Postgres. It will not `compose up postgres` (that recreates Tilt’s container; `init.sql` does not re-run on existing `pgdata`). Local `compose run` bind-mounts host models/src (same as `docker-compose.yml`); YAML/SQL/Python edits need no image rebuild. It skips `compose build` unless `BUILD=1` or `SKIP_BUILD=0` (Dockerfile / lockfile / package changes), then:

1. Alembic `upgrade head`
2. `pipeline run-once` (or `--force`) — see gates below
3. dbt `deps` + `seed` + `run` + `test` (the full project: box scores, standings, **PBP scoring + `fct_game_flow`**, and the rest — no separate PBP job). Skip tests with `RUN_DBT_TEST=0`; skip dbt with `SKIP_DBT=1`.
4. `ml python -m main score`
5. `dbt run --select stg_game_predictions+` so gold has tonight’s rows

**Gates** (`enabled` is the master switch):

|     | `season_active` (and window if set)                                                                                                                                       | Reddit (no separate flag)                                                                                                         |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| On  | Basketball daily: Scoreboard slate (Final + upcoming), Finals’ logs, **PBP for those Finals only**, standings, injuries, remaining-year contracts, odds if `ODDS_API_KEY` | Everyday r/nba posts (hot + top, `--time-filter day`, limit 50) plus top-10 comments per post. Off-season included. Not team subs |
| Off | Skip NBA steps                                                                                                                                                            | Still runs if `enabled` (`season_active` does not gate reddit)                                                                    |

`enabled` but not `season_active`: skip NBA, still run Reddit. Not `enabled`: skip everything (including Reddit). `--force` / `FORCE=1` bypasses `enabled` and the NBA season window so you can test basketball daily; it also runs Reddit. Missing `REDDIT_*` skips reddit HTTP (same pattern as odds). `scrape_mode=none` still skips NBA; Reddit still runs if enabled.

Disabled / nothing to do scrape status `skipped` exits 0 and does **not** run dbt. Reddit-only success still runs dbt. Scrape `failed` or dbt/ml failure exits non-zero.

**Not on daily / refresh:** teams/players directory (`scrape-all` / first load). Season-wide `scrape-play-by-play` (no `--game-id`) remains a manual backfill. Daily PBP is today’s Finals only and is enriched in that same dbt step. `--game-id` is ad-hoc recent games, then the same `dbt run`. Ungated `scrape-daily` is basketball only (no Reddit) and does include contracts.

## Slack and optional keys

| Env                                          | If unset                                                                    | Behavior when set                                                                                                                                                                                        |
| -------------------------------------------- | --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SLACK_WEBHOOK_URL`                          | no HTTP                                                                     | **One** Incoming Webhook per failed scrape sync (`pipeline` / `scrape-daily` / `scrape-all` / the scrape step of refresh-daily). Success is silent. Individual CLIs such as `scrape-games` do not alert. |
| `ODDS_API_KEY`                               | skip odds HTTP; daily still succeeds                                        | The Odds API upcoming h2h/spreads                                                                                                                                                                        |
| `REDDIT_CLIENT_ID` / `SECRET` / `USER_AGENT` | pipeline skips reddit HTTP; ungated `scrape-reddit` still fails before PRAW | Official Reddit API **posts** + top comments from r/nba → `source.reddit_posts` / `source.reddit_comments` (hot + top; modest comments-per-post)                                                         |

dbt and ml failures fail the shell. They do **not** send a second Slack post.

## Scheduling

Not started by `make up` / Tilt. After `make pipeline-enable`, prefer host cron:

For the Oracle VM, pass the registry coordinates so the prod overlay selects the images pulled from GHCR: `15 8 * * * cd /opt/nba && IMAGE_PREFIX=ghcr.io/<owner>/ IMAGE_TAG=latest make prod-refresh`.

Compose profile `cron` runs `python -m main pipeline run-once` only — **no dbt, no Elo**. Do not treat that container as a full refresh.

## Planned

Folding ml/dbt into the same Slack collector. Public host cron. Do not invent extra pages per step.
