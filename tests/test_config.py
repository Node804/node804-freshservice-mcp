"""Tests for the tool permission map.

Mode-gating semantics (hierarchy, env parsing, fallback) are enforced by
``node804_mcp_toolkit.ModeGate`` and tested in that package. These tests cover the
Freshservice-specific permission assignments.
"""

import pytest

from node804_mcp_toolkit import Mode


def _permissions():
    from node804_freshservice_mcp.config import TOOL_PERMISSIONS
    return TOOL_PERMISSIONS


VALID_MODES = {m.name.lower() for m in Mode}


class TestToolPermissionsMap:
    def test_all_values_are_valid_modes(self, mock_env):
        for tool, mode in _permissions().items():
            assert mode in VALID_MODES, f"{tool} has invalid mode '{mode}'"

    def test_read_tools_gated_read(self, mock_env):
        perms = _permissions()
        assert perms["get_tickets"] == "read"
        assert perms["get_ticket_by_id"] == "read"

    def test_writes_require_standard(self, mock_env):
        perms = _permissions()
        assert perms["create_ticket"] == "standard"
        assert perms["update_ticket"] == "standard"

    def test_destructive_deletes_require_admin(self, mock_env):
        perms = _permissions()
        assert perms["delete_ticket"] == "admin"
        assert perms["delete_change"] == "admin"

    def test_subrecord_deletes_require_full(self, mock_env):
        perms = _permissions()
        assert perms["delete_ticket_time_entry"] == "full"
        assert perms["delete_change_note"] == "full"
        assert perms["delete_change_task"] == "full"
        assert perms["delete_change_time_entry"] == "full"

    def test_renamed_tools(self, mock_env):
        perms = _permissions()
        assert "get_agent_group_by_id" in perms
        assert "get_requester_by_id" in perms
        assert "get_product_by_id" in perms
        assert "getAgentGroupById" not in perms
        assert "get_requester_id" not in perms
        assert "get_products_by_id" not in perms
