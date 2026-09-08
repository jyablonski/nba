# Docs

Guides for how this NBA analytics monorepo fits together. They favor short prose over bullet dumps; the root README still has the architecture diagram and quick start.

[Architecture](architecture.md) is who talks to whom (Compose profiles, gold vs source, API layers). [Data](data.md) is first load plus scrape → `source` → dbt → `silver`/`gold` and Cube on gold. [Operations](operations.md) is the daily scrape → dbt → Elo loop, Slack, and optional keys. [ML](ml.md) is how to run Elo `eval` / `score` today. [Frontend](frontend.md) covers the Next.js app and how it talks only to FastAPI. [Ask](ask.md) is HTTP `POST /api/v1/query` (`rules` vs `llm` over Cube). [MCP and AI](mcp-and-ai.md) describes the live MCP Cube tools and clearly labels planned NLP / AI work. [Testing](testing.md) is Make targets, coverage, and what GitHub Actions runs.

For agent conventions and service pins, see [AGENTS.md](../AGENTS.md).

## Plans

- [OCI + Caddy hosting](plans/oci-caddy-hosting.md) — Caddyfile, prod compose overlay, and CI/deploy workflows are in the repo; go-live still needs OCI VM, DNS, and secrets
- [ML win predictions](plans/ml-win-predictions.md) — in progress: Elo v0 persists pregame WP after scrape + dbt + `services/ml score`; upcoming Scoreboard rows, BRef injury snapshot, and The Odds API ingest are current; logit / Courtline / `/ask` still planned; never live WP
- [Courtline Social tab](plans/social-tab.md) — planned: enrich current r/nba posts (entity link, topics, standout rank) into a REST `/social` feed; writers/RSS later; not a Courtline screen today
- [Ask LLM / agent providers](plans/ask-llm-providers.md) — planned: use Cursor Pro via MCP (not as Courtline's LLM); local OpenAI-compatible (Ollama) for browser `/ask` without a vendor invoice; hosted keys stay opt-in; no LLM → SQL
- [Provider-independent identity migration](plans/provider-independent-identity-migration.md) — implemented clean-slate path: Basketball-Reference ingest with Baseline-owned UUIDs for teams, players, and games plus provider crosswalks
