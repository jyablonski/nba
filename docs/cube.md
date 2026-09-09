# Cube semantic layer

Cube is the semantic query service for NBA analytics. It exposes governed measures and dimensions over the `gold` schema. Ask and MCP use Cube; the browser does not call it directly. There is no gold-SQL fallback.

## Role and request flow

The data path is `scraper` → `source` → dbt → `silver` / `gold` → Cube → Ask and MCP. Alembic owns `source`, dbt owns warehouse models, and Cube reads `gold`. Cube does not scrape, run dbt, or write warehouse data. If dbt has not built a gold table, Cube queries can be empty or fail.

Cube lives in [`services/cube`](../services/cube/). [`cube.js`](../services/cube/cube.js) configures Postgres and the model path. YAML cubes are in [`model/cubes`](../services/cube/model/cubes/); reusable views are in [`model/views`](../services/cube/model/views/). A cube defines dimensions, measures, joins, and the gold relation or SQL expression behind them.

The main endpoints are:

- `/cubejs-api/v1/meta` — lists available cubes, measures, dimensions, and other queryable members.
- `/cubejs-api/v1/load` — accepts Cube query JSON: `measures`, `dimensions`, `filters`, `timeDimensions`, `order`, and `limit`.

Cube validates members and generates warehouse SQL internally. API and MCP send query JSON, not SQL. Their clients use `CUBEJS_API_SECRET`, load Cube meta, validate member names, and turn Cube failures into clear application errors. `Unknown Cube member(s)` means the member was absent from the running instance's meta; the Postgres column may still exist.

Cube is not a second warehouse. Its results depend on the current `gold` tables and the model in the running image. Refreshing dbt data does not update the model; changing YAML requires development sync locally or a new Cube image in production.

## Local and production

The local stack starts Cube with `make up` / Tilt. Tilt syncs `cube.js` and `model/` into the development container, and Compose publishes port 4000. Compose clients use `http://cube:4000`; a host process uses `http://localhost:4000`.

The production overlay starts Cube with Postgres, API, frontend, MCP, and Caddy. Cube is private to the Compose network at `http://cube:4000`; port 4000 is not published. Postgres is separately published on `POSTGRES_PORT` for DBeaver, while containers still use `postgres:5432`. MCP is published on host port 8001 at `/mcp` and requires `MCP_API_TOKEN`. Cube has a 1 GB memory limit.

Production images include the model. A YAML change must be included in the Cube image pushed to GHCR, then pulled by Oracle.

| Variable                                                                                                   | Purpose                                                                                           |
| ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `CUBE_API_URL`                                                                                             | Cube base URL. Compose uses `http://cube:4000`; local host processes use `http://localhost:4000`. |
| `CUBEJS_API_SECRET`                                                                                        | Shared Cube/API/MCP request secret. Keep it out of logs and source control.                       |
| `CUBEJS_DEV_MODE`                                                                                          | Development/security mode. Local defaults to `true`; production sets it to `false`.               |
| `CUBEJS_DB_TYPE`, `CUBEJS_DB_HOST`, `CUBEJS_DB_PORT`, `CUBEJS_DB_NAME`, `CUBEJS_DB_USER`, `CUBEJS_DB_PASS` | Cube's Postgres connection.                                                                       |

### Development mode and production debugging

`CUBEJS_DEV_MODE=true` makes local iteration easier by relaxing authentication and member-level access checks. This can hide a model problem: a member may work locally but be absent from production meta. Keep production at `false`; do not enable dev mode on the public host. See Cube's [admin/deployment guidance](https://docs.cube.dev/admin) and [dimension visibility documentation](https://docs.cube.dev/reference/data-modeling/dimensions).

Check production meta from the API container, which uses the same network and secret as Ask:

```bash
$dc exec -T api python -c '
import os
from cube.client import CubeClient

meta = CubeClient(
    os.environ["CUBE_API_URL"],
    os.environ["CUBEJS_API_SECRET"],
).meta()
players = next(c for c in meta["cubes"] if c["name"] == "players")
print([d["name"] for d in players.get("dimensions", [])])
'
```

After the new image is available:

```bash
cd /opt/nba
IMAGE_PREFIX=ghcr.io/<owner>/ IMAGE_TAG=<commit-sha> make prod-release
```

This pulls tagged images, runs the migration gate, recreates the stack, checks Cube through the API container, and reloads Caddy. If the model changed but meta did not, check the image tag and force-recreate Cube/API; refreshing Postgres data alone is not enough.

## Dimension visibility and `public: true`

Cube primary-key dimensions are private by default. `primary_key: true` still supports row identity and joins, but Cube may omit the member from `/meta`. Since API and MCP validate members against `/meta`, a hidden key fails before `/load` runs.

Product-facing primary keys need both properties:

```yaml
- name: player_id
  sql: player_id
  type: string
  primary_key: true
  public: true
```

This repository explicitly exposes identifiers such as `players.player_id`, `teams.team_id`, and `games_schedule.game_id`. Tests also require every Cube primary-key dimension to declare `public: true`. That setting controls semantic visibility; it does not publish port 4000 or replace authentication.

When adding a queryable member:

1. Add the dimension or measure to the appropriate Cube YAML over a gold relation.
2. Set `public: true` if a primary key is used by API, MCP, or Ask.
3. Update the named operation and tests when adding a rules or MCP wrapper.
4. Check `/meta` and run the Cube tests before publishing the image.

Fix model visibility or the requested member list rather than adding a gold-SQL fallback.

## Rules versus LLM Ask engine

`POST /api/v1/query` is the browser-facing Ask endpoint. `NLP_BACKEND` selects its natural-language provider; MCP's direct tools are unchanged.

| Backend         | Configuration                                                                       | Behavior                                                                                                                                                                                                                                                |
| --------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Rules (default) | `NLP_BACKEND=rules` or unset                                                        | Regex/alias classification for supported B2B, season-stat, player-compare, arena-city, salary/payroll, and standings questions. The matched handler calls a named Cube operation. Unsupported questions get a capability message. No LLM key is needed. |
| LLM (opt-in)    | `NLP_BACKEND=llm`, `NLP_LLM_API_KEY`; optional `NLP_LLM_BASE_URL` / `NLP_LLM_MODEL` | Sends the question to an OpenAI-compatible chat API with Cube meta as context, then uses a bounded tool loop over the same named operations and `query_cube`. It does not generate or execute SQL.                                                      |

Both backends depend on Cube and use the same semantic members. If Cube is down, Ask/MCP reports that the semantic layer is unavailable; neither falls back to gold SQL. Rules is the default because it is deterministic, local, and key-free. LLM is an operator choice with added key, cost, privacy, rate-limit, and model-availability concerns.

Related docs: [Ask and NLP backends](ask.md), [MCP and AI](mcp-and-ai.md), [Data](data.md), and [Operations](operations.md).
