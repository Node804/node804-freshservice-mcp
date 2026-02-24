"""Freshservice MCP server entry point."""

import logging
import sys
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from .config import get_mode, get_mode_summary, is_tool_allowed
from . import client as _client_mod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load permission mode
CURRENT_MODE = get_mode()
mode_info = get_mode_summary(CURRENT_MODE)
logger.info(
    f"Freshservice MCP starting in '{CURRENT_MODE}' mode - "
    f"{mode_info['tools_enabled']}/{mode_info['tools_total']} tools enabled"
)

# Create MCP instance
mcp = FastMCP("freshservice_mcp")


def conditional_tool():
    """Decorator that registers a tool only if allowed by the current mode."""
    def decorator(func):
        if is_tool_allowed(func.__name__, CURRENT_MODE):
            return mcp.tool()(func)
        else:
            logger.info(f"Tool '{func.__name__}' blocked by mode '{CURRENT_MODE}'")
            return func
    return decorator


# Always-on tools: available regardless of mode

@mcp.tool()
async def server_status() -> Dict[str, Any]:
    """Show the current Freshservice MCP server configuration.
    Returns the permission mode, which tool categories are enabled,
    the cache TTL, and the last-known API rate-limit status."""
    summary = get_mode_summary()
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


# When run via `python -m freshservice_mcp.server`, this module executes as
# __main__ but is NOT registered in sys.modules as 'freshservice_mcp.server'.
# Tool modules that do `from ..server import conditional_tool` would then
# re-import this file, creating a second mcp instance that main() never runs.
# Registering ourselves here prevents that double-import.
sys.modules.setdefault("freshservice_mcp.server", sys.modules[__name__])

# Import tool modules to trigger registration via @conditional_tool()
from . import tools  # noqa: E402, F401


def main():
    logger.info(f"Starting Freshservice MCP server (mode: {CURRENT_MODE})")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
