"""Tests for the permission configuration system."""

import os
import pytest


def _import_config():
    """Import config fresh (must happen after env vars are set by fixture)."""
    from freshservice_mcp.config import (
        get_mode,
        is_tool_allowed,
        get_allowed_tools,
        get_mode_summary,
        MODE_HIERARCHY,
        TOOL_PERMISSIONS,
    )
    return get_mode, is_tool_allowed, get_allowed_tools, get_mode_summary, MODE_HIERARCHY, TOOL_PERMISSIONS


class TestModeHierarchy:
    def test_read_is_lowest(self, mock_env):
        *_, MODE_HIERARCHY, _ = _import_config()
        assert MODE_HIERARCHY["read"] == 0

    def test_admin_is_highest(self, mock_env):
        *_, MODE_HIERARCHY, _ = _import_config()
        assert MODE_HIERARCHY["admin"] == 3

    def test_hierarchy_order(self, mock_env):
        *_, MODE_HIERARCHY, _ = _import_config()
        assert MODE_HIERARCHY["read"] < MODE_HIERARCHY["standard"]
        assert MODE_HIERARCHY["standard"] < MODE_HIERARCHY["full"]
        assert MODE_HIERARCHY["full"] < MODE_HIERARCHY["admin"]


class TestIsToolAllowed:
    def test_read_tool_allowed_in_read_mode(self, mock_env):
        _, is_tool_allowed, *_ = _import_config()
        assert is_tool_allowed("get_tickets", "read") is True

    def test_write_tool_blocked_in_read_mode(self, mock_env):
        _, is_tool_allowed, *_ = _import_config()
        assert is_tool_allowed("create_ticket", "read") is False

    def test_admin_tool_allowed_in_admin_mode(self, mock_env):
        _, is_tool_allowed, *_ = _import_config()
        assert is_tool_allowed("delete_ticket", "admin") is True

    def test_admin_tool_blocked_in_standard_mode(self, mock_env):
        _, is_tool_allowed, *_ = _import_config()
        assert is_tool_allowed("delete_ticket", "standard") is False

    def test_unknown_tool_blocked(self, mock_env):
        _, is_tool_allowed, *_ = _import_config()
        assert is_tool_allowed("nonexistent_tool", "admin") is False

    def test_full_tool_allowed_in_admin_mode(self, mock_env):
        _, is_tool_allowed, *_ = _import_config()
        assert is_tool_allowed("create_product", "admin") is True

    def test_full_tool_blocked_in_standard_mode(self, mock_env):
        _, is_tool_allowed, *_ = _import_config()
        assert is_tool_allowed("create_product", "standard") is False


class TestRenamedTools:
    """Verify the three renamed tool keys exist in TOOL_PERMISSIONS."""

    def test_get_agent_group_by_id_exists(self, mock_env):
        *_, TOOL_PERMISSIONS = _import_config()
        assert "get_agent_group_by_id" in TOOL_PERMISSIONS

    def test_get_requester_by_id_exists(self, mock_env):
        *_, TOOL_PERMISSIONS = _import_config()
        assert "get_requester_by_id" in TOOL_PERMISSIONS

    def test_get_product_by_id_exists(self, mock_env):
        *_, TOOL_PERMISSIONS = _import_config()
        assert "get_product_by_id" in TOOL_PERMISSIONS

    def test_old_names_removed(self, mock_env):
        *_, TOOL_PERMISSIONS = _import_config()
        assert "getAgentGroupById" not in TOOL_PERMISSIONS
        assert "get_requester_id" not in TOOL_PERMISSIONS
        assert "get_products_by_id" not in TOOL_PERMISSIONS


class TestGetModeSummary:
    def test_read_mode_no_create(self, mock_env):
        _, _, _, get_mode_summary, *_ = _import_config()
        summary = get_mode_summary("read")
        assert summary["capabilities"]["create"] is False

    def test_admin_mode_all_enabled(self, mock_env):
        _, _, _, get_mode_summary, *_ = _import_config()
        summary = get_mode_summary("admin")
        assert summary["capabilities"]["admin"] is True
        assert summary["tools_blocked"] == 0

    def test_tool_counts_consistent(self, mock_env):
        _, _, _, get_mode_summary, _, TOOL_PERMISSIONS = _import_config()
        summary = get_mode_summary("standard")
        assert summary["tools_enabled"] + summary["tools_blocked"] == summary["tools_total"]
        assert summary["tools_total"] == len(TOOL_PERMISSIONS)


class TestGetMode:
    def test_default_mode(self, monkeypatch):
        monkeypatch.setenv("FRESHSERVICE_DOMAIN", "test.freshservice.com")
        monkeypatch.setenv("FRESHSERVICE_APIKEY", "test_key")
        monkeypatch.delenv("FRESHSERVICE_MODE", raising=False)
        get_mode, *_ = _import_config()
        # With FRESHSERVICE_MODE unset, should default to "standard"
        # (Note: module-level caching means we test the function directly)
        monkeypatch.setenv("FRESHSERVICE_MODE", "")
        # Empty string is not valid, falls back to standard
        assert get_mode() == "standard"

    def test_invalid_mode_falls_back(self, monkeypatch):
        monkeypatch.setenv("FRESHSERVICE_DOMAIN", "test.freshservice.com")
        monkeypatch.setenv("FRESHSERVICE_APIKEY", "test_key")
        monkeypatch.setenv("FRESHSERVICE_MODE", "superadmin")
        get_mode, *_ = _import_config()
        assert get_mode() == "standard"
