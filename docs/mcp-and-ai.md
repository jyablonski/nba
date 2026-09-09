# MCP

`services/mcp` exposes NBA analytics as MCP tools for LLM hosts like Claude Desktop, so an agent can query the warehouse without writing SQL.

It is a FastMCP server over the Cube semantic layer. Ask uses the same named operations — see [ask.md](ask.md).

## Running it

Local: stdio by default (`uv run src/server.py`). MCP starts with the default Compose stack; scraper and dbt stay in profile `tools`.

Production: Streamable HTTP at `/mcp` on host port 8001. Clients must send `Authorization: Bearer $MCP_API_TOKEN`.

Two separate secrets, easy to confuse:

- `MCP_API_TOKEN` authenticates a **client to MCP**
- `CUBEJS_API_SECRET` authenticates **MCP to Cube**

MCP never opens Postgres. Cube down means a clear tool error, never a gold-SQL fallback. Empty gold tables mean empty results — run scraper and dbt first.

## Tools

Player and career:

- `search_players` — fuzzy name search
- `get_player_game_log` — box scores, season optional
- `get_player_season_stats` — PPG/RPG/APG by season
- `get_career_stats`, `compare_players`
- `get_player_back_to_backs` — B2B splits vs overall

Team and league:

- `get_team_record` — W/L plus filters (opponent, home/away, arena city, season)
- `get_standings` — conference table; falls back to Regular Season W–L when official rows are missing
- `get_team_payroll`, `get_player_contract` — remaining-year snapshots, not a paid ledger

Games and feeds:

- `get_games_schedule` — all-status slate, upcoming scores null
- `get_game_predictions` — Elo pregame WP, not a betting line
- `get_play_by_play` — actions for one game
- `get_player_injuries`, `get_game_odds` — current snapshots
- `get_reddit_posts` — r/nba posts; comments are reachable via `query_cube`

Escape hatch:

- `query_cube` — Cube query JSON (`measures`, `dimensions`, `filters`, `timeDimensions`, `limit`). Unknown members are rejected.

Free-form gold SQL (`query_nba_data`) was removed and is not coming back.

## Resources and prompts

- `nba://schema` — Cube meta, not gold DDL
- `nba://examples` — example questions mapped to tools
- Prompts: `analyze_player`, `compare_careers`, `team_performance`

## Adding a tool

Cube member → optional rules intent on `/ask` → the same named MCP tool (or just `query_cube`).

Do not add a gold-SQL helper to the API or MCP.

## Not built

Streaming, production LLM hardening, Cube SQL API and pre-aggregates, a historical paid-salary ledger, and a named `get_reddit_comments` tool.

Injuries, odds, PBP, Reddit, and Elo WP are queryable here but have no dedicated page in the UI.
