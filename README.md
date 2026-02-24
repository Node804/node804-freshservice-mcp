# Freshservice MCP Server

A configurable [MCP](https://modelcontextprotocol.io/) server for the [Freshservice](https://freshservice.com/) REST API with permission-based tool gating.

Freshservice only provides a single API key per account with no scoping. This server addresses that by introducing a `FRESHSERVICE_MODE` environment variable that controls which tools are exposed. Blocked tools are excluded at registration time, so the LLM never sees them.

## Permission Modes

| Mode | Tools | Description |
|------|-------|-------------|
| `read` | 50 | List, view, filter, search across all modules. No modifications. |
| `standard` | 72 | Read + create/update tickets, changes, approvals, service requests. No deletes, no agent/group admin. |
| `full` | 87 | Standard + products, requesters, solution articles, delete notes/tasks. No agent creation, no ticket/change deletion. |
| `admin` | 95 | Everything. Create/delete agents, groups, tickets, changes. |

Default mode is `standard`.

## Setup

### Prerequisites

- **Python 3.13+** — check with `python --version`
- **pip** — comes with Python
- A **Freshservice account** with API access enabled

### Getting Your Freshservice API Key

1. Log into your Freshservice portal as an agent
2. Click your **profile picture** in the top-right corner
3. Go to **Profile Settings**
4. Your API key is shown in the right sidebar under **Your API Key**
5. Copy it — you'll need it for configuration below

> **Note:** Freshservice provides a single API key per agent with no scoping. This is why the server has permission modes — so you can limit what the LLM can do, even though the API key itself has full access.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FRESHSERVICE_DOMAIN` | Yes | Your Freshservice domain (e.g. `yourcompany.freshservice.com`) |
| `FRESHSERVICE_APIKEY` | Yes | Your Freshservice API key |
| `FRESHSERVICE_MODE` | No | Permission mode: `read`, `standard`, `full`, or `admin`. Default: `standard` |
| `FRESHSERVICE_CACHE_TTL` | No | Cache lifetime in seconds for schema/reference data. Default: `3600` (1 hour). Set to `0` to disable caching. |

### Install

```bash
git clone <this-repo>
cd freshservice-mcp
pip install -e .
```

This installs the `freshservice-mcp` command and the `freshservice_mcp` Python module. The `-e` (editable) flag means changes you make to the source take effect immediately without reinstalling.

### Claude Desktop

1. Open your Claude Desktop config file:
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

2. Add the `freshservice-mcp` entry under `mcpServers` (create the file if it doesn't exist):

```json
{
  "mcpServers": {
    "freshservice-mcp": {
      "command": "python",
      "args": ["-m", "freshservice_mcp.server"],
      "env": {
        "FRESHSERVICE_APIKEY": "your_api_key",
        "FRESHSERVICE_DOMAIN": "yourcompany.freshservice.com",
        "FRESHSERVICE_MODE": "standard"
      },
      "cwd": "/path/to/freshservice-mcp"
    }
  }
}
```

3. Restart Claude Desktop — the server starts automatically when Claude needs it.

**Using a `.env` file instead of inline env values:**

If you'd rather keep credentials out of `claude_desktop_config.json`, create a `.env` file in the repo root (see `.env.example`) and use `cwd` to point the server at it:

```bash
cp .env.example .env   # edit with your credentials
```

```json
{
  "mcpServers": {
    "freshservice-mcp": {
      "command": "python",
      "args": ["-m", "freshservice_mcp.server"],
      "cwd": "/path/to/freshservice-mcp"
    }
  }
}
```

The server calls `load_dotenv()` on startup, which reads `.env` from the working directory. The `cwd` field tells Claude Desktop to start the server in the repo root where that file lives.

### Claude Code (CLI)

```bash
claude mcp add freshservice-mcp \
  -e FRESHSERVICE_APIKEY=your_api_key \
  -e FRESHSERVICE_DOMAIN=yourcompany.freshservice.com \
  -e FRESHSERVICE_MODE=standard \
  -- python -m freshservice_mcp.server
```

To verify it was added:

```bash
claude mcp list
```

### Verifying It Works

Once connected, ask your LLM:

- **"What's my access level?"** → calls `server_status`, shows the mode, tool count, and rate-limit info
- **"Who am I in Freshservice?"** → calls `get_current_agent`, confirms the API key is valid and returns your agent profile

If either fails, check the [Troubleshooting](#troubleshooting) section below.

## Project Structure

```
src/freshservice_mcp/
  __init__.py           # Package marker + version
  server.py             # FastMCP instance, conditional_tool decorator, main()
  config.py             # Permission modes, tool hierarchy, mode summary
  client.py             # Shared httpx client, rate-limit transport, response cache, auth
  models.py             # Enums (TicketSource, ChangeStatus, ...) + Pydantic models
  tools/
    __init__.py          # Imports all tool modules to trigger registration
    tickets.py           # 13 tools  - tickets + conversations
    changes.py           # 34 tools  - changes, approvals, notes, tasks, time entries
    service_catalog.py   # 3 tools   - service items + requests
    products.py          # 4 tools   - product CRUD
    requesters.py        # 6 tools   - requester CRUD + fields
    agents.py            # 7 tools   - current agent, agent CRUD + fields
    groups.py            # 10 tools  - agent groups + requester groups
    canned_responses.py  # 4 tools   - canned responses + folders
    workspaces.py        # 2 tools   - workspace listing
    solutions.py         # 13 tools  - KB categories, folders, articles
```

## Mode Details

### read

Safe for anyone who needs to look up ticket info, check change status, or search the knowledge base. Cannot modify anything.

Includes: get/list/filter/view operations for tickets, changes, agents, requesters, groups, products, service catalog, canned responses, workspaces, and solution articles.

### standard (default)

Day-to-day IT work. Create and update tickets, manage changes through their lifecycle, send replies, add notes, handle approvals. Cannot delete anything or manage agents/groups.

Includes everything in `read` plus: create/update tickets, create/update changes, close changes, ticket replies and notes, change tasks/notes/time entries, approval management, service requests.

### full

Adds content management and requester administration. For senior staff who need to manage the knowledge base and requester records.

Includes everything in `standard` plus: create/update products, create/update requesters, solution article/folder/category management, delete change notes/tasks/time entries, requester group membership.

### admin

Full access to everything, including destructive operations. Only use this if you specifically need to create agents, delete tickets or changes, or manage group structures.

Includes everything in `full` plus: delete tickets, delete changes, create/update agents, create/update agent groups, create/update requester groups.

## Prompt Examples

Once connected, you can ask things like:

| Prompt | What happens | API calls |
|--------|-------------|-----------|
| "Show me my open tickets" | `get_my_tickets` — looks up your agent ID, discovers all non-resolved statuses, and filters in one shot | 1 (warm cache) |
| "What's ticket #4521 about?" | `get_ticket_by_id` | 1 |
| "Create a ticket for the printer on floor 3" | `create_ticket` with subject/description/priority | 1 |
| "Add a note to ticket #4521 saying we ordered parts" | `create_ticket_note` | 1 |
| "Reply to ticket #4521 letting them know it's fixed" | `send_ticket_reply` | 1 |
| "Show all changes awaiting approval" | `filter_changes` with query `status:3` | 1 |
| "What ticket statuses do we have?" | `get_ticket_statuses` — returns every status categorized as resolved/unresolved | 0 (cached) |
| "Who am I in Freshservice?" | `get_current_agent` — returns your agent profile | 0 (cached) |
| "What's my access level?" | `server_status` — shows mode, tool counts, rate limit | 0 |
| "The admin added new statuses, refresh the cache" | `clear_cache` — drops all cached data | 0 |

## API Efficiency

Freshservice enforces a per-hour tenant-wide API rate limit. This server is designed to stay well within it:

- **1 tool call = 1 API call** for 91 of 95 tools. The server makes zero background calls, zero polling, and zero prefetching — every API call is triggered only when the LLM explicitly invokes a tool.
- **Compound convenience tools**: `get_my_tickets` chains agent lookup + status discovery + filter into a single tool call (1 API call on warm cache, up to 3 on first use). `get_ticket_statuses` parses cached field data at zero API cost.
- **Rate-limit handling**: A custom transport reads `X-RateLimit-Remaining` on every response and automatically retries on HTTP 429 with the `Retry-After` delay (up to 3 retries).
- **Response caching**: Schema and reference-data tools cache successful responses for the duration set by `FRESHSERVICE_CACHE_TTL` (default 1 hour). These are admin-configured structures that effectively never change mid-session. Repeated lookups cost zero API calls. Use the `clear_cache` tool to force a refresh.
- **Pagination controls**: All list endpoints expose `page` and `per_page` parameters so the LLM fetches only what it needs. Auto-paginating tools (`list_service_items`, `filter_agents`) default to 3 pages max.

## Always-On Tools

The `server_status` and `clear_cache` tools are always available regardless of mode.

- **`server_status`** — Reports the current mode, tool counts, capabilities, cache TTL, and API rate-limit remaining.
- **`clear_cache`** — Drops all cached responses so the next call fetches fresh data from the API.

## Security Notes

- API key is only sent to your Freshservice domain via Basic auth over HTTPS
- No telemetry, no external calls, no logging of credentials
- Credentials are validated at startup; the server fails fast if `FRESHSERVICE_DOMAIN` or `FRESHSERVICE_APIKEY` are missing
- Mode restriction is enforced at tool registration time. Blocked tools don't exist in the MCP server's tool list, so the LLM cannot call them.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `RuntimeError: FRESHSERVICE_DOMAIN environment variable is required` | Missing or empty `FRESHSERVICE_DOMAIN` | Make sure the `env` block in your MCP config has the correct variable name and value |
| `RuntimeError: FRESHSERVICE_APIKEY environment variable is required` | Missing or empty `FRESHSERVICE_APIKEY` | Same — check the `env` block, or your `.env` file if running from source |
| Server starts but tools return `401 Unauthorized` | Invalid API key | Regenerate your key in Freshservice Profile Settings and update your config |
| Server starts but tools return `404 Not Found` | Wrong domain format | Use the full domain (`yourcompany.freshservice.com`), not just the subdomain name |
| Tools you expect are missing | Mode is too restrictive | Check `server_status` to see the current mode, then set `FRESHSERVICE_MODE` to a higher level |
| `No module named freshservice_mcp` | Package not installed | Run `pip install -e .` from the repo root |
| Stale data after admin changes | Cached response | Ask the LLM to call `clear_cache`, or set `FRESHSERVICE_CACHE_TTL=0` to disable caching |

## Development

```bash
pip install -e ".[dev]"
pytest tests/
```

## Heritage & What Changed

Originally derived from [effytech/freshservice_mcp](https://github.com/effytech/freshservice_mcp), which provided a single-file proof of concept wiring Freshservice endpoints to MCP. Roughly 15-20% of the original code survives — mainly the basic API call patterns and endpoint URLs.

Everything else has been rewritten or added from scratch:

| Area | Original | Now |
|------|----------|-----|
| **Structure** | Single file, flat | Modular package — 10 tool modules, shared client, config, models |
| **Safety** | All tools exposed, single unscoped key | 4 permission modes; blocked tools excluded at registration time |
| **Rate limiting** | None | Auto-retry on 429 with `Retry-After`, rate-limit tracking via `server_status` |
| **Caching** | None | Configurable TTL cache on schema/reference data, `clear_cache` tool |
| **Pagination** | ~14 tools returned page 1 only | All list tools expose `page`/`per_page`; auto-paginators capped at 3 pages |
| **Convenience tools** | None | `get_my_tickets`, `get_ticket_statuses`, `get_current_agent` |
| **Tool descriptions** | Generic one-liners | Enum values, query syntax examples, cross-references, behavioral context |
| **Credential handling** | None | Validated at startup, fail-fast on missing env vars |
| **Tests** | None | 44 tests covering cache, rate-limiting, config, and convenience tools |
| **Tool count** | ~50 | 95 permission-gated + 2 always-on |

## License

MIT
