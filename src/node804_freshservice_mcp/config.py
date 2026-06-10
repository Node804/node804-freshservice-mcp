"""
Tool permission map for the Freshservice MCP server.

Which tools are exposed is controlled by the FRESHSERVICE_MODE env var,
enforced by ``node804_mcp_toolkit.ModeGate`` in ``server.py``. Modes:
  read       - Read-only access. List, view, filter, search. No modifications.
  standard   - Read + create/update tickets and changes. No deletes, no admin ops.
  full       - Standard + manage products, requesters, KB articles, and delete
               sub-records (notes, tasks, time entries).
  admin      - All operations: agent/group management and ticket/change deletes.

Default: read (least privilege — operators opt into write access explicitly)

Note: Freshservice issues one API key per agent, scoped to that agent's full
permissions — there is no read-only key. This mode gate is therefore the only
layer restricting what the LLM can do with the key.
"""

# Tool permission categories
# Each tool function name maps to the minimum mode required.
# Every @conditional_tool() function MUST appear here (enforced by
# tests/test_permissions.py); unknown tools are blocked at registration.
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
    "list_ticket_time_entries": "read",
    "view_ticket_time_entry": "read",

    # === TICKETS: WRITE ===
    "create_ticket": "standard",
    "update_ticket": "standard",
    "send_ticket_reply": "standard",
    "create_ticket_note": "standard",
    "update_ticket_conversation": "standard",
    "add_ticket_attachment": "standard",
    "add_note_attachment": "standard",
    "add_reply_attachment": "standard",
    "create_ticket_time_entry": "standard",
    "update_ticket_time_entry": "standard",

    # === TICKETS: DELETE ===
    "delete_ticket": "admin",
    "delete_ticket_attachment": "admin",
    "delete_conversation_attachment": "admin",
    "delete_ticket_time_entry": "full",

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
