"""
Configuration and permission management for Freshservice MCP server.

Controls which tools are exposed based on FRESHSERVICE_MODE env var.
Modes:
  read       - Read-only access. List, view, filter, search. No modifications.
  standard   - Read + create/update tickets and changes. No deletes, no admin ops.
  full       - Everything except destructive admin operations.
  admin      - All operations including agent/group management and deletes.

Default: standard
"""

import os
import logging

logger = logging.getLogger(__name__)

VALID_MODES = {"read", "standard", "full", "admin"}

# Tool permission categories
# Each tool function name maps to the minimum mode required
TOOL_PERMISSIONS = {
    # === TICKETS: READ ===
    "get_ticket_fields": "read",
    "get_ticket_statuses": "read",
    "get_my_tickets": "read",
    "get_tickets": "read",
    "get_ticket_by_id": "read",
    "filter_tickets": "read",
    "list_all_ticket_conversation": "read",
    "list_ticket_attachments": "read",

    # === TICKETS: WRITE ===
    "create_ticket": "standard",
    "update_ticket": "standard",
    "send_ticket_reply": "standard",
    "create_ticket_note": "standard",
    "update_ticket_conversation": "standard",
    "add_ticket_attachment": "standard",
    "add_note_attachment": "standard",
    "add_reply_attachment": "standard",

    # === TICKETS: DELETE ===
    "delete_ticket": "admin",
    "delete_ticket_attachment": "admin",
    "delete_conversation_attachment": "admin",

    # === CHANGES: READ ===
    "get_changes": "read",
    "get_change_by_id": "read",
    "filter_changes": "read",
    "list_change_fields": "read",
    "get_change_tasks": "read",
    "view_change_task": "read",
    "list_change_notes": "read",
    "view_change_note": "read",
    "list_change_time_entries": "read",
    "view_change_time_entry": "read",
    "list_change_approval_groups": "read",
    "view_change_approval": "read",
    "list_change_approvals": "read",

    # === CHANGES: WRITE ===
    "create_change": "standard",
    "update_change": "standard",
    "close_change": "standard",
    "create_change_note": "standard",
    "update_change_note": "standard",
    "create_change_task": "standard",
    "update_change_task": "standard",
    "create_change_time_entry": "standard",
    "update_change_time_entry": "standard",
    "move_change": "standard",

    # === CHANGES: APPROVALS (WRITE) ===
    "create_change_approval_group": "standard",
    "update_change_approval_group": "standard",
    "cancel_change_approval_group": "standard",
    "update_approval_chain_rule_change": "standard",
    "send_change_approval_reminder": "standard",
    "cancel_change_approval": "standard",

    # === CHANGES: DELETE ===
    "delete_change": "admin",
    "delete_change_note": "full",
    "delete_change_task": "full",
    "delete_change_time_entry": "full",

    # === SERVICE CATALOG: READ ===
    "list_service_items": "read",
    "get_requested_items": "read",

    # === SERVICE CATALOG: WRITE ===
    "create_service_request": "standard",

    # === PRODUCTS: READ ===
    "get_all_products": "read",
    "get_product_by_id": "read",

    # === PRODUCTS: WRITE ===
    "create_product": "full",
    "update_product": "full",

    # === REQUESTERS: READ ===
    "get_all_requesters": "read",
    "get_requester_by_id": "read",
    "list_all_requester_fields": "read",
    "filter_requesters": "read",

    # === REQUESTERS: WRITE ===
    "create_requester": "full",
    "update_requester": "full",

    # === AGENTS: READ ===
    "get_current_agent": "read",
    "get_agent": "read",
    "get_all_agents": "read",
    "filter_agents": "read",
    "get_agent_fields": "read",

    # === AGENTS: WRITE ===
    "create_agent": "admin",
    "update_agent": "admin",

    # === GROUPS: READ ===
    "get_all_agent_groups": "read",
    "get_agent_group_by_id": "read",
    "get_all_requester_groups": "read",
    "get_requester_groups_by_id": "read",
    "list_requester_group_members": "read",

    # === GROUPS: WRITE ===
    "add_requester_to_group": "full",
    "create_group": "admin",
    "update_group": "admin",
    "create_requester_group": "admin",
    "update_requester_group": "admin",

    # === CANNED RESPONSES: READ ===
    "get_all_canned_response": "read",
    "get_canned_response": "read",
    "list_all_canned_response_folder": "read",
    "list_canned_response_folder": "read",

    # === WORKSPACES: READ ===
    "list_all_workspaces": "read",
    "get_workspace": "read",

    # === SOLUTIONS/KB: READ ===
    "get_all_solution_category": "read",
    "get_solution_category": "read",
    "get_list_of_solution_folder": "read",
    "get_solution_folder": "read",
    "get_list_of_solution_article": "read",
    "get_solution_article": "read",

    # === SOLUTIONS/KB: WRITE ===
    "create_solution_category": "full",
    "update_solution_category": "full",
    "create_solution_article": "full",
    "update_solution_article": "full",
    "create_solution_folder": "full",
    "update_solution_folder": "full",
    "publish_solution_article": "full",

    # === LOCAL FILES: READ ===
    "find_file": "read",
}

# Mode hierarchy - each mode includes all permissions of lower modes
MODE_HIERARCHY = {
    "read": 0,
    "standard": 1,
    "full": 2,
    "admin": 3,
}


def get_mode() -> str:
    """Get the configured permission mode from environment."""
    mode = os.getenv("FRESHSERVICE_MODE", "standard").lower().strip()
    if mode not in VALID_MODES:
        logger.warning(f"Invalid FRESHSERVICE_MODE '{mode}', falling back to 'standard'")
        return "standard"
    return mode


def is_tool_allowed(tool_name: str, mode: str = None) -> bool:
    """Check if a tool is allowed under the current mode."""
    if mode is None:
        mode = get_mode()

    required_mode = TOOL_PERMISSIONS.get(tool_name)
    if required_mode is None:
        # Unknown tool - block by default
        logger.warning(f"Unknown tool '{tool_name}' not in permission map, blocking")
        return False

    return MODE_HIERARCHY[mode] >= MODE_HIERARCHY[required_mode]


def get_allowed_tools(mode: str = None) -> set:
    """Return set of tool names allowed for the current mode."""
    if mode is None:
        mode = get_mode()
    return {name for name in TOOL_PERMISSIONS if is_tool_allowed(name, mode)}


def get_mode_summary(mode: str = None) -> dict:
    """Return a summary of what's enabled for the current mode."""
    if mode is None:
        mode = get_mode()

    allowed = get_allowed_tools(mode)
    total = len(TOOL_PERMISSIONS)

    return {
        "mode": mode,
        "tools_enabled": len(allowed),
        "tools_total": total,
        "tools_blocked": total - len(allowed),
        "capabilities": {
            "read": True,
            "create": MODE_HIERARCHY[mode] >= MODE_HIERARCHY["standard"],
            "update": MODE_HIERARCHY[mode] >= MODE_HIERARCHY["standard"],
            "delete": MODE_HIERARCHY[mode] >= MODE_HIERARCHY["admin"],
            "admin": MODE_HIERARCHY[mode] >= MODE_HIERARCHY["admin"],
        },
    }
