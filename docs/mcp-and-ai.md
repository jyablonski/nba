# MCP and AI

This document separates what exists today from what is only planned. The MCP server is real against the Cube semantic layer (YAML over gold). HTTP natural-language query has two interchangeable backends: an in-house rules engine (the **default**) and an opt-in LLM adapter. Both call Cube. Deeper product features (streaming, auth, public SQL) are not built yet.

## Purpose

MCP exposes structured NBA analytics tools to LLM hosts (for example Claude Desktop) so an agent can search players, pull game logs, compare careers, filter team records, read remaining-contract / payroll snapshots, pull conference standings, and query schedule / Elo WP / injuries / odds / PBP / reddit without writing SQL. Ad-hoc questions use `query_cube` (Cube query JSON, validated against meta).

## Use case

Wire `services/mcp` into an MCP-capable client when you want chat-driven analytics over the same Cube model Ask uses. Operators still need scraper + dbt first; empty `gold` tables mean empty Cube results. MCP starts in the default local and production Compose stacks; scraper and dbt remain in profile `tools`. MCP needs Cube (`CUBE_API_URL`, `CUBEJS_API_SECRET`); Cube down → clear tool error, no gold SQL fallback.

## How it works today

The server is FastMCP (`uv run src/server.py`, stdio for clients). It reads Cube (`CUBE_API_URL`, default host `http://localhost:4000`) with `CUBEJS_API_SECRET`. Python pin is **3.14**. It does not open Postgres for query tools.

Named tools (Cube wrappers):

- `search_players` — fuzzy name search
- `get_player_game_log` — box scores (season optional)
- `get_player_back_to_backs` — B2B splits vs overall (`total_back_to_backs`, `games_played_in_b2b` minutes>0, `games_sat_in_b2b`)
- `get_career_stats` — totals and averages
- `compare_players` — side-by-side career rows (`stats` optional)
- `get_team_record` — W/L plus filtered games (opponent, home/away, arena city, season / since)
- `get_player_contract` — remaining-season salary snapshot; optional `season` reads `player_contracts`
- `get_team_payroll` — team payroll snapshot; optional `season` reads `team_payroll`
- `get_standings` — conference table (season and conference optional). Official Cube `standings` first; empty season → Regular Season `team_games` W–L ranks (same overlay as REST)
- `get_player_season_stats` — PPG / RPG / APG by season
- `get_games_schedule` — all-status slate (upcoming scores null)
- `get_game_predictions` — Elo pregame `model_wp`, `as_of`, `model_version` (not a betting line)
- `get_player_injuries` — current BRef injury snapshot
- `get_game_odds` — current Odds API slate snapshot (not a book)
- `get_play_by_play` — actions for one `game_id` (sane limit; season-scoped ingest)
- `get_reddit_posts` — PRAW rows (limit, optional title search). No Courtline page. Comments live on Cube `reddit_comments` (query via `query_cube`); no named `get_reddit_comments` tool yet
- `query_cube` — Cube load JSON (`measures`, `dimensions`, `filters`, `timeDimensions`, `limit`); unknown members rejected

`query_nba_data` (free-form gold SQL) is **removed**.

Resources:

- `nba://schema` — Cube meta (cubes, measures, dimensions), not gold DDL
- `nba://examples` — example questions with tool mappings

Prompts:

- `analyze_player(player_name)` — guided player analysis
- `compare_careers(player_a, player_b)` — side-by-side compare
- `team_performance(team_name, city?)` — team record analysis

Example host wiring: run `uv` with `--directory …/services/mcp` and `CUBE_API_URL` / `CUBEJS_API_SECRET` set, as noted in `services/mcp/src/server.py`.

## Adding a use case

Cube member → optional rules intent on `/ask` → same MCP tool (or `query_cube`). Do not add a gold SQL helper in API or MCP.

## Related surfaces (current)

FastAPI `POST /api/v1/query` is the only browser NL surface (`/ask` posts here; the frontend does not call MCP or Cube). The API selects a backend from `NLP_BACKEND`:

| Backend             | How to enable                                                                           | What it does                                                                                                                                                                                                                                                                      |
| ------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **rules** (default) | `NLP_BACKEND=rules` or unset                                                            | In-house regex/alias engine (`NaturalLanguageQueryService` / `RulesNlpProvider`). Families: B2B, season averages, career compare, arena-city W–L, salary/payroll, standings. Each handler is a Cube query. Unrecognized questions get a capability message and HTTP 200, not 501. |
| **llm** (opt-in)    | `NLP_BACKEND=llm` plus `NLP_LLM_API_KEY`, optional `NLP_LLM_BASE_URL` / `NLP_LLM_MODEL` | Calls an OpenAI-compatible chat API with Cube meta in the system prompt and a tool-calling loop over the **same named Cube operations** as MCP plus `query_cube`. Missing key → HTTP 200 refuse, no tool execution.                                                               |

Do not set `NLP_BACKEND=llm` on the public host without a key, spend controls, and a decision to send user questions to a third party.

Public `/ask` stays **option A** (rules) unless an operator explicitly flips the backend. Option B (LLM → Cube tools) is the modular adapter above. Option C (LLM → SQL) is not current on HTTP or MCP.

Injuries / odds / PBP / reddit / Elo WP / full slate are queryable via Cube/MCP/Ask tools. Courtline has no new screens for them and no win-prob badge.

## Planned (not built)

These ideas appear in product direction but must not be described as present behavior:

Streaming replies in `/ask`. A production-hardened LLM product (retries, auth, rate limits, eval against a hosted model). Cursor Pro as MCP host vs Courtline `/ask` providers: [plans/ask-llm-providers.md](plans/ask-llm-providers.md). Cube SQL API / pre-aggregates. Cube on the 12GB production VM (off today). Historical paid-salary ledger (BRef remaining-year snapshot is current). Courtline win-prob badge / “who wins tonight”.

Label anything in this section as future work when writing code or docs elsewhere.
