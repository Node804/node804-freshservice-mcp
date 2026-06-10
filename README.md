# Freshservice MCP Server

A configurable [MCP](https://modelcontextprotocol.io/) server for the [Freshservice](https://freshservice.com/) REST API with permission-based tool gating.

Freshservice only provides a single API key per account with no scoping. This server addresses that by introducing a `FRESHSERVICE_MODE` environment variable that controls which tools are exposed. Blocked tools are excluded at registration time, so the LLM never sees them.

## Permission Modes

| Mode | Tools | Description |
|------|-------|-------------|
| `read` | 54 | List, view, filter, search across all modules. File search. No modifications. |
| `standard` | 81 | Read + create/update tickets, changes, approvals, service requests, attachments, time entries. No deletes, no agent/group admin. |
| `full` | 97 | Standard + products, requesters, solution articles, delete notes/tasks/time entries. No agent creation, no ticket/change deletion. |
| `admin` | 107 | Everything. Create/delete agents, groups, tickets, changes, attachments. |

Default mode is `read`.

## Setup

### Prerequisites

- **[uv](https://docs.astral.sh/uv/)** (recommended) — manages Python and dependencies for you, with hash-verified installs
  - or **Python 3.11+** with pip
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
| `FRESHSERVICE_MODE` | No | Permission mode: `read`, `standard`, `full`, or `admin`. Default: `read` |
| `FRESHSERVICE_CACHE_TTL` | No | Cache lifetime in seconds for schema/reference data. Default: `3600` (1 hour). Set to `0` to disable caching. |
| `FRESHSERVICE_FILE_SEARCH_PATHS` | No | Semicolon-separated list of directories the `find_file` tool can search (e.g. `C:\Users\me\Docs;C:\Exports`). Required for file discovery. |
| `FRESHSERVICE_AUDIT_LOG` | No | Path to a JSON-lines audit log (e.g. `C:\logs\freshservice-audit.jsonl`). Every tool call is logged with sanitized arguments, success/error state, and timing. Disabled when unset. |

### Install

**Option A — uv (recommended).** No install step at all: `uvx` fetches the package from PyPI on first run and caches it. Pin the version so upgrades are deliberate:

```bash
uvx node804-freshservice-mcp==1.2.0
```

**Option B — pip:**

```bash
pip install node804-freshservice-mcp
```

**Option C — from source (development):**

```bash
git clone <this-repo>
cd node804-freshservice-mcp
uv sync          # or: pip install -e ".[dev]"
```

Each option provides the `node804-freshservice-mcp` command and the `node804_freshservice_mcp` Python module.

### Claude Desktop

1. Open your Claude Desktop config file:
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

2. Add the `node804-freshservice-mcp` entry under `mcpServers` (create the file if it doesn't exist):

```json
{
  "mcpServers": {
    "FreshService": {
      "command": "uvx",
      "args": ["node804-freshservice-mcp==1.2.0"],
      "env": {
        "FRESHSERVICE_APIKEY": "your_api_key",
        "FRESHSERVICE_DOMAIN": "yourcompany.freshservice.com",
        "FRESHSERVICE_MODE": "standard",
        "FRESHSERVICE_CACHE_TTL": 3600
      }
    }
  }
}
```

If you installed with pip instead of uv, use `"command": "python"` with `"args": ["-m", "node804_freshservice_mcp.server"]`.

3. Restart Claude Desktop — the server starts automatically when Claude needs it.

**Using a `.env` file instead of inline env values:**

If you'd rather keep credentials out of `claude_desktop_config.json`, create a `.env` file in the repo root (see `.env.example`) and use `cwd` to point the server at it:

```bash
cp .env.example .env   # edit with your credentials
```

```json
{
  "mcpServers": {
    "node804-freshservice-mcp": {
      "command": "uvx",
      "args": ["node804-freshservice-mcp==1.2.0"],
      "cwd": "/path/to/node804-freshservice-mcp"
    }
  }
}
```

The server calls `load_dotenv()` on startup, which reads `.env` from the working directory. The `cwd` field tells Claude Desktop to start the server in the repo root where that file lives.

### Claude Code (CLI)

```bash
claude mcp add node804-freshservice-mcp \
  -e FRESHSERVICE_APIKEY=your_api_key \
  -e FRESHSERVICE_DOMAIN=yourcompany.freshservice.com \
  -e FRESHSERVICE_MODE=standard \
  -- uvx node804-freshservice-mcp==1.2.0
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
src/node804_freshservice_mcp/
  __init__.py           # Package marker + version
  server.py             # FastMCP instance, conditional_tool decorator, main()
  config.py             # Permission modes, tool hierarchy, mode summary
  client.py             # Shared httpx client, rate-limit transport, response cache, auth
  models.py             # Enums (TicketSource, ChangeStatus, ...) + Pydantic models
  tools/
    __init__.py          # Imports all tool modules to trigger registration
    tickets.py           # 24 tools  - tickets, conversations, attachments, time entries
    changes.py           # 33 tools  - changes, approvals, notes, tasks, time entries
    service_catalog.py   # 3 tools   - service items + requests
    products.py          # 4 tools   - product CRUD
    requesters.py        # 6 tools   - requester CRUD + fields
    agents.py            # 7 tools   - current agent, agent CRUD + fields
    groups.py            # 10 tools  - agent groups + requester groups
    canned_responses.py  # 4 tools   - canned responses + folders
    workspaces.py        # 2 tools   - workspace listing
    solutions.py         # 13 tools  - KB categories, folders, articles
    files.py             # 1 tool    - local file search for attachment discovery
```

## Mode Details

### read (default)

Safe for anyone who needs to look up ticket info, check change status, or search the knowledge base. Cannot modify anything.

Includes: get/list/filter/view operations for tickets, changes, agents, requesters, groups, products, service catalog, canned responses, workspaces, and solution articles.

### standard

Day-to-day IT work. Create and update tickets, manage changes through their lifecycle, send replies, add notes, handle approvals. Cannot delete anything or manage agents/groups.

Includes everything in `read` plus: create/update tickets, create/update changes, close changes, ticket replies and notes, attachments, change tasks/notes/time entries, approval management, service requests.

### full

Adds content management and requester administration. For senior staff who need to manage the knowledge base and requester records.

Includes everything in `standard` plus: create/update products, create/update requesters, solution article/folder/category management, delete change notes/tasks/time entries, requester group membership.

### admin

Full access to everything, including destructive operations. Only use this if you specifically need to create agents, delete tickets or changes, or manage group structures.

Includes everything in `full` plus: delete tickets, delete changes, create/update agents, create/update agent groups, create/update requester groups.

## Attachments

The server provides attachment tools for uploading, listing, and deleting files on tickets.

### Finding files

Use `find_file` to search for files on the local filesystem by partial name or glob pattern before attaching them. This is the recommended first step when a user asks to find, locate, or attach files from their system — for example, asking to "attach the Q4 report" will find `Q4_Report.pdf` in any configured search directory.

Searches are restricted to directories listed in the `FRESHSERVICE_FILE_SEARCH_PATHS` environment variable (semicolon-separated). Matching is case-insensitive and supports partial names (`report`), glob patterns (`*.pdf`), and recursive subdirectory search.

### Uploading

Use `add_ticket_attachment`, `add_note_attachment`, and `add_reply_attachment` to upload files. These tools take an absolute file path on the MCP server's local filesystem, read the file, detect MIME type, and upload it via multipart form-data.

> **Note:** The MCP server must have filesystem access to the file being attached. These tools are designed for scenarios where the MCP client (e.g. Claude Code) runs on the same machine or can write files to a path the server can read.

### Listing and deleting

- `list_ticket_attachments` — list all attachments on a ticket (read mode)
- `delete_ticket_attachment` / `delete_conversation_attachment` — remove attachments (admin mode)

> **Freshservice limit:** The total size of all attachments on a single ticket cannot exceed 40 MB.

## Agent Signatures

The `send_ticket_reply` and `add_reply_attachment` tools automatically append the current agent's HTML signature to every outbound reply. The signature is pulled from your Freshservice agent profile (the same one configured under **Profile Settings → Signature** in the Freshservice portal).

- Signature data comes from the cached `get_current_agent` call, so there is **zero additional API cost**.
- If no signature is configured in your profile, replies are sent without one.
- Internal notes (`create_ticket_note`, `add_note_attachment`) are **not** affected — signatures are only appended to replies visible to the requester.

## Prompt Examples

Once connected, you can ask things like:

| Prompt | What happens | API calls |
|--------|-------------|-----------|
| "Show me my open tickets" | `get_my_tickets` — looks up your agent ID, discovers all non-resolved statuses, and filters in one shot | 1 (warm cache) |
| "What's ticket #4521 about?" | `get_ticket_by_id` | 1 |
| "Create a ticket for the printer on floor 3" | `create_ticket` with subject/description/priority | 1 |
| "Add a note to ticket #4521 saying we ordered parts" | `create_ticket_note` | 1 |
| "Reply to ticket #4521 letting them know it's fixed" | `send_ticket_reply` — auto-appends your agent signature | 1 |
| "Find that Q4 report" | `find_file` — searches configured directories for matching files | 0 |
| "Attach this screenshot to ticket #4521" | `add_ticket_attachment` with the file path | 1 |
| "Show all changes awaiting approval" | `filter_changes` with query `status:3` | 1 |
| "What ticket statuses do we have?" | `get_ticket_statuses` — returns every status categorized as resolved/unresolved | 0 (cached) |
| "Who am I in Freshservice?" | `get_current_agent` — returns your agent profile | 0 (cached) |
| "What's my access level?" | `server_status` — shows mode, tool counts, rate limit | 0 |
| "The admin added new statuses, refresh the cache" | `clear_cache` — drops all cached data | 0 |

## API Efficiency

Freshservice enforces a per-hour tenant-wide API rate limit. This server is designed to stay well within it:

- **1 tool call = 1 API call** for most tools. The server makes zero background calls, zero polling, and zero prefetching — every API call is triggered only when the LLM explicitly invokes a tool. Attachment uploads use multipart form-data and count as a single API call each.
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
| `No module named node804_freshservice_mcp` | Package not installed | Use the `uvx` config (installs automatically), or run `pip install node804-freshservice-mcp` |
| Stale data after admin changes | Cached response | Ask the LLM to call `clear_cache`, or set `FRESHSERVICE_CACHE_TTL=0` to disable caching |

## Development

```bash
uv sync                # creates .venv from pyproject.toml + uv.lock
uv run pytest tests/
```

Or with pip: `pip install -e ".[dev]"` then `pytest tests/`.

`uv.lock` pins the full dependency graph with hashes for reproducible installs. After changing dependencies in `pyproject.toml`, run `uv lock` and commit the updated lockfile.

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
| **Tests** | None | 55 tests covering cache, rate-limiting, config, permission-map consistency, convenience tools, and attachments |
| **Tool count** | ~50 | 107 permission-gated + 2 always-on |

## AI-Assisted Development

Portions of this project including code, tests, and documentation were developed with the assistance of generative AI (Anthropic's Claude). All changes are human-reviewed before merge and exercised by the automated test suite, but as with any software, review the code and test against a non-production Freshservice instance before trusting it with write access (`standard` mode or above) to a live tenant.

## License

MIT
