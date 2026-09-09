# Frontend

`services/frontend` is the Next.js app users see. It is a thin client: every screen goes through the FastAPI REST API.

It never talks to Postgres, Cube, or MCP. Keep it that way — see `services/frontend/AGENTS.md` for package-local rules.

## How it works

App Router, TanStack Query for fetches, UI in `src/components`, typed client in `src/lib/api.ts`.

URLs come from `NEXT_PUBLIC_API_URL`, which is a **build-time ARG**. It defaults to `http://localhost:8000`; production bakes the public origin into the image. An empty value must never fall through to localhost.

The product name is **Baseline**. One header bar holds the lockup, tabs, and a last-scraped watermark from `GET /api/v1/status` — never API health.

## Pages

Tabs: **Home · Games · Schedule · Players · Teams · Compare · Ask · About**

- `/` — coverage facts, latest completed games with PBP links, East/West standings snapshot
- `/games` — completed-game picker for play-by-play
- `/games/[id]` — scoring-differential chart, time-led %, max lead, lead changes, biggest scoring run. Team brand colors come from the API; not live win probability
- `/schedule` — upcoming slate (not Final, date ≥ today). No scores, odds, or WP
- `/players`, `/players/[id]` — directory with search and filters; profile with career bar, game log, contract snapshot, B2B splits, PPG-by-season
- `/players/compare` — up to N players, sortable, difference row. With exactly two, a head-to-head toggle shows games they played on opposite teams
- `/teams`, `/teams/[id]` — conference/division tables, scoring scatter, team profile with cap position and filterable game log
- `/standings` — full conference tables (deep link, not a tab)
- `/ask` — posts to `POST /api/v1/query`. One question, one answer, no transcript
- `/about` — sources and coverage in plain language
- `/admin` — operator console, GitHub OAuth. Not in the nav. See [operations.md](operations.md)

Season defaults to the latest loaded season everywhere; `?season=` is still honored but the picker is hidden.

Standings prefer official `fct_standings`; when those rows are missing, rank and games-behind are derived from Regular Season W–L.

## Rules that keep being worth restating

**Honest empty states.** User-facing copy says "nothing to show yet" — never scrape CLI names, dbt, gold, make targets, or pipeline internals. Those belong in operator docs, not in front of a visitor.

**Salary is a snapshot.** Contract and payroll UI must be labeled a Basketball-Reference **remaining-year snapshot**, not a historical paid ledger. Unmatched names render `—`, never `$0` or an invented number.

**No new backends.** Do not add SQL, Cube, or MCP calls from the browser. `NLP_BACKEND=llm` is an API-side switch only.

**Nulls render `—`.** Including the watermark, which shows `Scraped —` when missing.

## Running and testing

```bash
cd services/frontend && npm install && npm run dev   # standalone
make up                                             # full stack with hot reload
make test-frontend                                  # Vitest
make test-frontend-e2e                              # Playwright
```

## Not built

A Social tab for r/nba content. Injuries, odds, and Reddit have gold marts and are reachable through Ask and MCP, but they are not pages.

Also not built: betting features, streaming Ask, live in-game win probability, a season-leaders API.
