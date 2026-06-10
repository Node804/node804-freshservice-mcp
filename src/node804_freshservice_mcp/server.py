"""Freshservice MCP server entry point.

Tool registration goes through ``node804_mcp_toolkit.ModeGate``, which composes
RBAC gating with optional audit logging. Tool modules call
``@conditional_tool()`` unchanged — the shim looks up each tool's required
mode from ``config.TOOL_PERMISSIONS`` and delegates to the gate.

When ``FRESHSERVICE_AUDIT_LOG=/path/to/audit.jsonl`` is set, every tool call
emits one JSON-lines event with sanitized arguments, success/error state,
and timing — provided automatically by the gate.
"""

import logging
import sys
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP
from node804_mcp_toolkit import Mode, ModeGate, open_sink

from . import client as _client_mod
from .config import TOOL_PERMISSIONS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Toolkit-driven setup ---------------------------------------------------

# Audit sink — no-op when FRESHSERVICE_AUDIT_LOG is unset, costs nothing.
_audit_sink = open_sink(env_var="FRESHSERVICE_AUDIT_LOG")

# RBAC gate. Least-privilege default: read-only unless the operator
# explicitly opts into write access via FRESHSERVICE_MODE.
gate = ModeGate.from_env(
    env_var="FRESHSERVICE_MODE",
    default=Mode.READ,
    audit_sink=_audit_sink,
)

CURRENT_MODE = gate.mode.name.lower()

mcp = FastMCP("node804_freshservice_mcp")


def conditional_tool():
    """Backwards-compatible decorator that registers a tool only if allowed.

    Tool modules call ``@conditional_tool()`` unchanged. This shim looks up
    the required mode for the tool's function name in ``TOOL_PERMISSIONS``
    and delegates to ``node804_mcp_toolkit.ModeGate.tool``. The gate handles both
    mode gating and (when configured) audit wrapping.
    """

    def decorator(func):
        name = func.__name__
        required_str = TOOL_PERMISSIONS.get(name)
        if required_str is None:
            # Unknown tool — block by not registering. Same behavior as before
            # the toolkit refactor.
            logger.warning(f"Unknown tool '{name}' not in permission map, blocking")
            return func
        required = Mode[required_str.upper()]
        return gate.tool(mcp, required=required)(func)

    return decorator


# Always-on tools: available regardless of mode


@mcp.tool()
async def server_status() -> Dict[str, Any]:
    """Show the current Freshservice MCP server configuration.

    Returns the permission mode, enabled/blocked tool lists from the live
    gate registry, audit destination, cache TTL, and last-known API
    rate-limit status.
    """
    summary = gate.summary()
    summary["audit"] = _audit_sink.describe()
    summary["rate_limit"] = {
        "remaining": _client_mod.rate_limit_remaining,
        "total": _client_mod.rate_limit_total,
    }
    summary["cache_ttl_seconds"] = _client_mod.CACHE_TTL
    return summary


@mcp.tool()
async def clear_cache() -> Dict[str, Any]:
    """Clear all cached API responses.

    Use this when you know data has changed (e.g. new custom statuses,
    updated ticket fields) and the cached values are stale."""
    count = _client_mod.clear_response_cache()
    return {"success": True, "entries_cleared": count}


# When run via `python -m node804_freshservice_mcp.server`, this module executes as
# __main__ but is NOT registered in sys.modules as 'node804_freshservice_mcp.server'.
# Tool modules that do `from ..server import conditional_tool` would then
# re-import this file, creating a second mcp instance that main() never runs.
# Registering ourselves here prevents that double-import.
sys.modules.setdefault("node804_freshservice_mcp.server", sys.modules[__name__])

# Import tool modules to trigger registration via @conditional_tool()
from . import tools  # noqa: E402, F401

# Log after registration so the counts reflect the live gate registry.
logger.info(
    f"Freshservice MCP starting: {gate.describe()} "
    f"(audit: {_audit_sink.describe()})"
)


def main():
    logger.info(f"Starting Freshservice MCP server (mode: {CURRENT_MODE})")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
