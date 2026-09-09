# Operations

What to run day to day. Scrape commands and marts are in [data.md](data.md).

## Bring-up

```bash
cp .env.example .env
make up             # Tilt: postgres, migrate, cube, api, frontend, mcp
make db-migrate     # after new Alembic revisions
```

Keep `DATABASE_URL` in sync with the Postgres settings. `docker compose down -v` deletes the warehouse — only run it deliberately.

Cube uses 400–800 MB, so production caps it at 1 GB. Watch VM memory when a refresh runs alongside the always-on stack.

## The daily gate

`source.scrape_pipeline` is a single row that decides what runs. It ships **disabled**.

```bash
make pipeline-enable     # enabled + season_active
make pipeline-status
make scrape              # scrape only; FORCE=1 bypasses the gate
make dbt                 # deps + build
make ml                  # Elo score, then the gold copy
make refresh             # scrape → dbt → ml
```

`enabled` is the master switch. `season_active` gates the NBA steps only:

|                             | NBA steps                                                                    | Reddit                           |
| --------------------------- | ---------------------------------------------------------------------------- | -------------------------------- |
| `enabled` + `season_active` | slate, Finals logs, their PBP, standings, injuries, contracts, odds if keyed | yes                              |
| `enabled` only              | skipped                                                                      | yes — Reddit is not season-gated |
| not `enabled`               | skipped                                                                      | skipped                          |

`FORCE=1` bypasses both. A skipped run exits 0 and does **not** run dbt.

`refresh-daily.sh` runs Alembic, the gated scrape, `dbt build`, Elo, then the gold predictions copy. It waits for an existing healthy Postgres rather than starting one, because recreating Tilt's container would not re-run `init.sql`.

`dbt build` interleaves each model's tests with the model, so a failing test skips that model's descendants instead of publishing them and failing at the end.

## Optional keys

| Variable            | Unset                              | Set                                                             |
| ------------------- | ---------------------------------- | --------------------------------------------------------------- |
| `SLACK_WEBHOOK_URL` | silent                             | one post per **failed** sync, never per step. Success is silent |
| `ODDS_API_KEY`      | odds skipped, daily still succeeds | The Odds API upcoming slate                                     |
| `REDDIT_*`          | Reddit skipped                     | r/nba posts and top comments                                    |

dbt and ml failures fail the shell but do not send a second Slack post.

## Scheduling

Three cron entries on the VM. None of this starts with `make up`.

```cron
15 8  * * * cd /opt/nba && flock -n /tmp/nba-refresh.lock make prod-refresh >> /opt/nba/logs/refresh-daily.log 2>&1
45 11 * * * cd /opt/nba && make prod-check-freshness >> /opt/nba/logs/freshness.log 2>&1
*     * * * * cd /opt/nba && make prod-admin-jobs >> /opt/nba/logs/admin-jobs.log 2>&1
```

**Use `make prod-refresh`, never `make refresh-daily`.** The latter is the local target: it skips the prod overlay and resolves bare `nba-*:latest` instead of the GHCR images — and it does not fail loudly, because Compose just builds the image on the box from the working tree. `/opt/nba/logs/` must also exist, or the redirect fails before `make` runs and the error goes to mail nobody reads.

The second entry is the **absence check**. Every other signal is emitted _by_ the pipeline, so a pipeline that never starts is completely silent — which is exactly how one outage went unnoticed. It needs only Postgres and `curl`, so it survives the failures that break the refresh. It alerts when `now() - last_success_at` exceeds `STALE_HOURS` (default 26) and exits 0 when the pipeline is intentionally disabled.

Cron carries no registry coordinates: `prod-release` writes the tag it deployed to `.env.deploy`, which every make target includes. CI pins `IMAGE_TAG=<sha>`, so the nightly job and the API serving traffic are the same build. Precedence is command line > environment > `.env.deploy` > defaults, so a rollback still wins.

## Admin console

`/admin` shows ingestion, dbt, and ML health, and can re-run jobs. Two independent gates, both **fail closed**:

- **The page** uses GitHub OAuth with an `ADMIN_GITHUB_LOGINS` allowlist. Unset means nobody gets in, including you.
- **The API** (`/api/v1/admin/*`) needs `Authorization: Bearer $ADMIN_API_TOKEN`. Unset returns 503 — never open.

The token is held server-side and never reaches the browser.

Setup: generate `ADMIN_API_TOKEN` and `AUTH_SECRET`, create a GitHub OAuth app with callback `<origin>/api/auth/callback/github`, then set `AUTH_GITHUB_ID`, `AUTH_GITHUB_SECRET`, `AUTH_URL`, and `ADMIN_GITHUB_LOGINS`. All are commented in `.env.example`; with none set the console is simply unreachable.

## Admin jobs

The console queues work into `source.admin_jobs` and `scripts/admin-job-runner.sh` runs it on the host. Four types: `scrape`, `dbt`, `ml`, `refresh`.

The API cannot execute jobs itself — it has no Docker socket, and giving a publicly reachable process one would be root-equivalent on the box. It only ever inserts a row.

What the runner guarantees:

- **One job at a time**, enforced by a partial unique index. A second request gets 409.
- **Never overlaps the daily refresh** — it shares the same `flock`. A busy lock re-queues the job rather than failing it.
- **Abandoned jobs are reaped.** A runner killed mid-job would otherwise leave its row `running` forever, wedging the queue. Before claiming, it fails any `running` row whose lock is free and is older than `STALE_JOB_GRACE` (default 5 minutes).

`make test-admin-jobs` exercises all of this against the local stack; it needs a running Postgres, so it is not in CI.

**Deploys are deliberately not a button.** CI runs `make prod-deploy` on push to `main` and `workflow_dispatch` is enabled, so a redeploy is one click in the Actions tab — no SSH, no extra code.

## Also worth knowing

Production publishes Postgres on `POSTGRES_PORT` for tools like DBeaver, while containers keep using `postgres:5432`. Allow the port in the OCI security list and any host firewall; credentials live in `/opt/nba/.env`.

Not built: per-source retry (re-running one failed source rather than a whole step), and folding dbt and ml failures into the Slack collector.
