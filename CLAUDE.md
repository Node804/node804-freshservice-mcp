# CLAUDE.md

Project-level instructions for Claude Code when working on this repository.

## Authoritative API Reference

The **only** documentation source for Freshservice API endpoints, parameters, response formats, and behavior is:

**https://api.freshservice.com/**

Do not use third-party blogs, Stack Overflow, or other unofficial sources when adding or modifying tools. Always verify endpoint paths, required fields, query parameters, and response schemas against the official docs before writing code.

## Project Overview

This is an MCP (Model Context Protocol) server that wraps the Freshservice REST API v2 with permission-based tool gating. The `FRESHSERVICE_MODE` environment variable controls which tools are exposed to the LLM.

## Key Architecture

- **src-layout** Python package using hatchling build backend
- **`server.py`** — FastMCP instance + `conditional_tool()` decorator. Tool modules are imported at the bottom to avoid circular imports.
- **`config.py`** — Every tool function name must be listed in `TOOL_PERMISSIONS` with its minimum required mode. New tools that aren't in this map will be blocked by default.
- **`client.py`** — Shared `httpx.AsyncClient` singleton with `RateLimitTransport` (429 retry + header tracking) and `TTLCache` / `@cached_response` for caching.
- **`tools/`** — One module per Freshservice domain (tickets, changes, agents, etc). Each tool uses `@conditional_tool()` and calls `get_client()` for HTTP access.

## Adding a New Tool

1. Add the async function in the appropriate `tools/*.py` module with `@conditional_tool()`.
2. Add the function name to `TOOL_PERMISSIONS` in `config.py` with the correct minimum mode (`read`, `standard`, `full`, or `admin`).
3. If the tool returns rarely-changing data, add `@cached_response()` below `@conditional_tool()`. TTL is controlled by `FRESHSERVICE_CACHE_TTL` env var (default 3600s). Only override with `@cached_response(ttl_seconds=N)` if a tool genuinely needs a different TTL.
4. All list endpoints must accept `page` and `per_page` parameters and return pagination metadata.
5. Run `pytest tests/` and verify the tool count in the smoke test.

## Tool Selection Guide

When the user asks about their tickets, use the convenience tools instead of manually chaining lower-level calls. This saves API calls and avoids wasting tokens on plumbing.

### "My tickets" / "My open tickets"

Use `get_my_tickets(status_filter="unresolved")`. Do NOT manually call `get_current_agent` → `get_ticket_fields` → parse statuses → `filter_tickets`. The compound tool does all of that internally and its dependencies are cached.

- `status_filter="unresolved"` (default) — everything except Resolved/Closed
- `status_filter="resolved"` — only Resolved and Closed
- `status_filter="all"` — every ticket assigned to the agent

### Status lookups

Use `get_ticket_statuses` to get categorized status IDs. Do NOT call `get_ticket_fields` and parse the status choices yourself. The tool returns `resolved_ids`, `unresolved_ids`, and a full `statuses` list with categories.

### Agent identity

Use `get_current_agent` whenever you need the authenticated user's agent ID, email, or group memberships. It is cached for the session — call it freely without worrying about API cost.

### File discovery

Use `find_file` to search for files on the local filesystem before using attachment tools. When the user asks to find, locate, or attach files from their system, always call `find_file` first. Searches are restricted to directories listed in `FRESHSERVICE_FILE_SEARCH_PATHS` (semicolon-separated). The tool supports partial names (`report`), glob patterns (`*.pdf`), and is case-insensitive. Results include absolute paths, sizes, and modified timestamps. Default limit is 25 results.

### Attachments

Use `add_ticket_attachment`, `add_note_attachment`, and `add_reply_attachment` to upload files. Each takes an absolute `file_path` on the MCP server's filesystem — the server reads the file, detects MIME type, and uploads it via multipart form-data. The total attachment size per ticket cannot exceed 40 MB (Freshservice limit).

When the user provides a partial filename or isn't sure of the exact path, call `find_file` first to resolve the full path, then pass it to the attachment tool.

To list or delete attachments, use `list_ticket_attachments`, `delete_ticket_attachment`, or `delete_conversation_attachment`.

### Time entries

Use `list_ticket_time_entries` and `view_ticket_time_entry` to read time logged against a ticket. Use `create_ticket_time_entry` to log new work (requires `time_spent` in "hh:mm" format, `note`, and `agent_id`). The optional `billable` flag marks whether the entry is billable. Use `update_ticket_time_entry` to modify an existing entry's time, note, or billable status. `delete_ticket_time_entry` permanently removes an entry (requires `full` mode).

Equivalent tools exist for changes (`*_change_time_entry`).

### Ticket approvals

Use `list_ticket_approvals` to see who must approve a ticket, along with each approver's stage and decision (requested/approved/rejected). Use `view_ticket_approval` to fetch a single approval record by its `approval_id`. Both are read-only.

Equivalent tools exist for changes (`list_change_approvals`, `view_change_approval`).

### Filter query syntax

The `filter_tickets` and `filter_changes` tools accept a query string with this syntax:

- Single condition: `"status:2"`
- AND: `"status:2 AND priority:1"`
- OR: `"status:2 OR status:3"`
- Grouped: `"agent_id:123 AND (status:2 OR status:3)"`

Field names match the Freshservice API field names (e.g., `agent_id`, `status`, `priority`, `requester_id`, `group_id`, `type`).

### Pagination

All list tools default to `page=1, per_page=30`. Only request additional pages if the user asks for more results or pagination metadata indicates `has_more: true`. Do not auto-paginate through all pages unless explicitly asked.

### Cache behavior

Schema and reference data (`get_ticket_fields`, `get_ticket_statuses`, `get_current_agent`, `list_change_fields`, etc.) are cached for the duration of `FRESHSERVICE_CACHE_TTL` (default 1 hour). If the user says data has changed, call `clear_cache` before retrying the lookup.

## Testing

```bash
pip install -e ".[dev]"
pytest tests/
```

Tests use `monkeypatch` to set fake credentials. No real API calls are made in tests.
