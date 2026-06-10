"""Consistency checks between TOOL_PERMISSIONS and the live gate registry.

Imports the server (in admin mode, via conftest) so every tool module runs
its ``@conditional_tool()`` decorators, then verifies the static permission
map and the actual decorated functions never drift apart. A tool missing
from the map would be silently blocked in production; a stale map entry
would misreport capabilities in ``server_status``.
"""

import pytest


@pytest.fixture()
def server(mock_env):
    from node804_freshservice_mcp import server as srv
    return srv


class TestPermissionMapConsistency:
    def test_every_decorated_tool_is_in_permission_map(self, server):
        decorated = set(server.gate.all_known_tools)
        mapped = set(server.TOOL_PERMISSIONS)
        missing = decorated - mapped
        assert not missing, (
            f"Tools decorated with @conditional_tool() but missing from "
            f"TOOL_PERMISSIONS (silently blocked): {sorted(missing)}"
        )

    def test_every_map_entry_has_a_decorated_function(self, server):
        decorated = set(server.gate.all_known_tools)
        mapped = set(server.TOOL_PERMISSIONS)
        stale = mapped - decorated
        assert not stale, (
            f"TOOL_PERMISSIONS entries with no matching tool function "
            f"(stale map entries): {sorted(stale)}"
        )

    def test_admin_mode_registers_everything(self, server):
        # conftest sets FRESHSERVICE_MODE=admin, the highest tier
        summary = server.gate.summary()
        assert summary["mode"] == "admin"
        assert summary["tools_blocked"] == 0
        assert summary["tools_enabled"] == len(server.TOOL_PERMISSIONS)

    def test_server_status_reports_live_registry(self, server):
        import asyncio

        result = asyncio.run(server.server_status())
        assert result["tools_total"] == len(server.TOOL_PERMISSIONS)
        assert "enabled_tools" in result
        assert "rate_limit" in result
        assert "cache_ttl_seconds" in result
