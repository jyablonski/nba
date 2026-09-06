# Ask and NLP backends

HTTP natural-language query: `POST /api/v1/query`. Optional body field `season` (Courtline `/ask` sends the header season). Courtline `/ask` posts here and nowhere else ([frontend.md](frontend.md)). MCP named tools and `query_cube` are [mcp-and-ai.md](mcp-and-ai.md) — this file is the API switch and the in-process query layer only.

## Purpose

Document the **current** backends and what `/ask` will not do, so agents do not invent a SQL window or a second NLP stack. Courtline `/ask` is a bounded warehouse Q&A: it shows only the latest question and answer, not a stacked conversation.

## Enable

| Backend             | Env                                                                                                                                           | Current behavior                                                                                                                                                               |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **rules** (default) | `NLP_BACKEND=rules` or unset                                                                                                                  | In-house regex/alias engine. No API key. Each matched family runs a Cube query.                                                                                                |
| **llm** (opt-in)    | `NLP_BACKEND=llm` plus `NLP_LLM_API_KEY`; optional `NLP_LLM_BASE_URL` / `NLP_LLM_MODEL` (defaults `https://api.openai.com/v1`, `gpt-4o-mini`) | OpenAI-compatible chat + tool loop over Cube (`query_cube` + named Cube wrappers). System context is Cube **meta**, not gold DDL. Missing key → HTTP **200** refuse, no tools. |

Do not set `NLP_BACKEND=llm` on a public host without a key, spend controls, and a decision to send questions to a third party. Public `/ask` stays rules unless an operator flips it.

Factory: `services/api/src/services/nlp/factory.py`. Unknown `NLP_BACKEND` raises at build time.

Ask/MCP require `CUBE_API_URL` (compose: `http://cube:4000`). Cube down or unset → HTTP 200 with a clear “Cube semantic layer is down” message. There is **no** gold SQL fallback.

## Rules families (current)

`NaturalLanguageQueryService` / `RulesNlpProvider` classifies then answers via `CubeAnalytics`. Families: **b2b**, **season_stats** (tight: `PPG/RPG/APG` + `by/per/each season`), **compare**, **arena_city**, **salary** / payroll, **standings**. Unrecognized or empty questions return a capability message and HTTP 200, not 501.

Season: `_extract_season` (`YYYY-YY` in the question) wins; else the optional request `season` (header). Used for B2B (omit = career), standings (omit = latest official `fct_standings` season, else latest Regular Season `team_games` season), and arena-city (in addition to `since`). Standings prefer Cube `standings`; when that cube is empty for the season, ranks come from Regular Season `team_games` W–L (same overlay REST uses). Salary/payroll stay remaining-year dim snapshots unless the question names a contract season (`player_contracts` / `team_payroll`).

Examples the `/ask` page already suggests: Kawhi B2Bs, LeBron vs Curry career games, Warriors in Chicago since 2010-11, Curry salary, Warriors payroll, who leads the West.

Salary/payroll answers are Basketball-Reference **remaining-year snapshots**, not a historical ledger.

## Adding a use case

1. Add or reuse a Cube measure/dimension (YAML over gold).
2. Optional rules intent in `nl_query.py` that calls `CubeAnalytics`.
3. Same named tool is available on MCP / LLM (`query_cube` or a thin wrapper).

Do not add a gold SQL string in API or MCP.

## Query modules (not a second dialect)

REST list/detail routes still read gold via `queries/` + `repositories/`. Ask does not:

- `cube/` — REST client (`/load`, `/meta`), query JSON builders, `CubeAnalytics` named operations
- `services/nl_query.py` — rules classification and prose
- `services/nlp/` — `NlpProvider` protocol, rules wrapper, llm client/prompt/tools

The llm backend calls the **same named Cube operations** as MCP (`search_players`, `get_player_game_log`, `get_player_back_to_backs`, `get_career_stats`, `compare_players`, `get_team_record`, `get_player_contract`, `get_team_payroll`, `get_standings`, `get_player_season_stats`, `get_games_schedule`, `get_game_predictions`, `get_player_injuries`, `get_game_odds`, `get_play_by_play`, `get_reddit_posts`, `query_cube`). Max four tool rounds. It does not emit SQL.

## No SQL on HTTP (current)

`query_nba_data` is gone. `query_cube` accepts Cube query JSON only (measures, dimensions, filters), validated against Cube meta. Unknown members are rejected. Executor still accepts the old name `run_cube_query` as an alias.

Response `sql` on rules answers is a provenance string (`cube:…`), not a statement the client runs.

## Planned (not current)

Streaming `/ask`. Production LLM hardening (retries, auth, rate limits, hosted eval). Local OpenAI-compatible / Cursor-MCP provider story: [plans/ask-llm-providers.md](plans/ask-llm-providers.md). Cube SQL API / pre-aggregates. `/ask` “who wins tonight” (Elo is queryable via `get_game_predictions`; there is no rules family and Courtline has no win-prob badge — see [ml.md](ml.md)). Cube on the 12GB production VM (off today; Ask fails clearly without it).
