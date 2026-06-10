"""Change management tools (core, approvals, notes, tasks, time entries)."""

from typing import Any, Dict, List, Optional, Union

from ..server import conditional_tool
from ..client import get_client, parse_link_header, cached_response, api_error
from ..models import ChangeStatus, ChangePriority, ChangeImpact, ChangeType, ChangeRisk


# ============================================================
# Core Changes
# ============================================================


@conditional_tool()
async def get_changes(
    page: Optional[int] = 1,
    per_page: Optional[int] = 30,
    query: Optional[str] = None,
    view: Optional[str] = None,
    sort: Optional[str] = None,
    order_by: Optional[str] = None,
    updated_since: Optional[str] = None,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """List changes from Freshservice with optional inline filtering.

    For advanced filter queries (AND/OR logic), prefer filter_changes instead.

    Args:
        page: Page number (default: 1)
        per_page: Items per page (1-100, default: 30)
        query: Simple filter string (e.g., "priority:4 OR priority:3")
        view: Predefined view name — 'my_open', 'unassigned', etc.
        sort: Sort field — 'priority', 'created_at', 'updated_at', etc.
        order_by: 'asc' or 'desc' (default: 'desc')
        updated_since: Only changes updated after this ISO datetime
        workspace_id: Filter by workspace (0 = all workspaces)

    Note: query and view cannot be used together."""
    if page < 1:
        return {"error": "Page number must be greater than 0"}
    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    params: Dict[str, Any] = {"page": page, "per_page": per_page}
    if query:
        params["query"] = query
    if view:
        params["view"] = view
    if sort:
        params["sort"] = sort
    if order_by:
        params["order_by"] = order_by
    if updated_since:
        params["updated_since"] = updated_since
    if workspace_id is not None:
        params["workspace_id"] = workspace_id

    client = get_client()
    try:
        response = await client.get("/api/v2/changes", params=params)
        response.raise_for_status()

        pagination_info = parse_link_header(response.headers.get("Link", ""))
        return {
            "changes": response.json(),
            "pagination": {
                "current_page": page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "per_page": per_page,
            },
        }
    except Exception as e:
        return api_error("Failed to fetch changes", e)


@conditional_tool()
async def get_change_by_id(change_id: int) -> Dict[str, Any]:
    """Fetch a single change by its numeric ID.

    Returns full change details including subject, description, status,
    priority, impact, risk, type, planning fields, and timestamps."""
    client = get_client()
    try:
        response = await client.get(f"/api/v2/changes/{change_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to fetch change", e)


@conditional_tool()
async def create_change(
    requester_id: int,
    subject: str,
    description: str,
    priority: Union[int, str],
    impact: Union[int, str],
    status: Union[int, str],
    risk: Union[int, str],
    change_type: Union[int, str],
    group_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    department_id: Optional[int] = None,
    planned_start_date: Optional[str] = None,
    planned_end_date: Optional[str] = None,
    reason_for_change: Optional[str] = None,
    change_impact: Optional[str] = None,
    rollout_plan: Optional[str] = None,
    backout_plan: Optional[str] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a new change request in Freshservice.

    Args:
        requester_id: ID of the requester initiating the change
        subject: Change title
        description: Change body (HTML supported)
        priority: 1=Low, 2=Medium, 3=High, 4=Urgent
        impact: 1=Low, 2=Medium, 3=High
        status: 1=Open, 2=Planning, 3=Awaiting Approval, 4=Pending Release,
                5=Pending Review, 6=Closed
        risk: 1=Low, 2=Medium, 3=High, 4=Very High
        change_type: 1=Minor, 2=Standard, 3=Major, 4=Emergency
        planning_fields: reason_for_change, change_impact, rollout_plan,
                         backout_plan — each accepts a plain string"""
    try:
        priority_val = int(priority)
        impact_val = int(impact)
        status_val = int(status)
        risk_val = int(risk)
        change_type_val = int(change_type)
    except ValueError:
        return {"error": "Invalid value for priority, impact, status, risk, or change_type"}

    if (
        priority_val not in [e.value for e in ChangePriority]
        or impact_val not in [e.value for e in ChangeImpact]
        or status_val not in [e.value for e in ChangeStatus]
        or risk_val not in [e.value for e in ChangeRisk]
        or change_type_val not in [e.value for e in ChangeType]
    ):
        return {"error": "Invalid value for priority, impact, status, risk, or change_type"}

    data: Dict[str, Any] = {
        "requester_id": requester_id,
        "subject": subject,
        "description": description,
        "priority": priority_val,
        "impact": impact_val,
        "status": status_val,
        "risk": risk_val,
        "change_type": change_type_val,
    }
    if group_id:
        data["group_id"] = group_id
    if agent_id:
        data["agent_id"] = agent_id
    if department_id:
        data["department_id"] = department_id
    if planned_start_date:
        data["planned_start_date"] = planned_start_date
    if planned_end_date:
        data["planned_end_date"] = planned_end_date

    planning_fields: Dict[str, Any] = {}
    if reason_for_change:
        planning_fields["reason_for_change"] = {"description": reason_for_change}
    if change_impact:
        planning_fields["change_impact"] = {"description": change_impact}
    if rollout_plan:
        planning_fields["rollout_plan"] = {"description": rollout_plan}
    if backout_plan:
        planning_fields["backout_plan"] = {"description": backout_plan}
    if planning_fields:
        data["planning_fields"] = planning_fields

    if custom_fields:
        data["custom_fields"] = custom_fields

    client = get_client()
    try:
        response = await client.post("/api/v2/changes", json=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to create change", e)


@conditional_tool()
async def update_change(
    change_id: int,
    change_fields: Dict[str, Any],
) -> Dict[str, Any]:
    """Update fields on an existing change.

    Args:
        change_id: The change to update
        change_fields: Dict of field→value pairs.  Common fields:
            status, priority, impact, risk, agent_id, group_id.
            Nest custom fields under "custom_fields" and planning
            fields under "planning_fields" (plain strings accepted).

    To close a change with an explanation, prefer the close_change tool."""
    if not change_fields:
        return {"error": "No fields provided for update"}

    custom_fields = change_fields.pop("custom_fields", {})
    planning_fields = change_fields.pop("planning_fields", {})

    update_data = dict(change_fields)
    if custom_fields:
        update_data["custom_fields"] = custom_fields
    if planning_fields:
        formatted_planning = {}
        for field, value in planning_fields.items():
            if isinstance(value, str):
                formatted_planning[field] = {"description": value}
            else:
                formatted_planning[field] = value
        update_data["planning_fields"] = formatted_planning

    client = get_client()
    try:
        response = await client.put(f"/api/v2/changes/{change_id}", json=update_data)
        response.raise_for_status()
        return {
            "success": True,
            "message": "Change updated successfully",
            "change": response.json(),
        }
    except Exception as e:
        return {"success": False, **api_error("Failed to update change", e)}


@conditional_tool()
async def close_change(
    change_id: int,
    change_result_explanation: str,
    custom_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Close a change by setting status=Closed and recording the result.

    This is a convenience wrapper around update_change that sets the
    status to 6 (Closed) and writes the change_result_explanation
    custom field in one call."""
    update_data: Dict[str, Any] = {
        "status": ChangeStatus.CLOSED.value,
        "custom_fields": {"change_result_explanation": change_result_explanation},
    }
    if custom_fields:
        update_data["custom_fields"].update(custom_fields)
    return await update_change(change_id, update_data)


@conditional_tool()
async def delete_change(change_id: int) -> Dict[str, Any]:
    """Permanently delete a change.  This cannot be undone."""
    client = get_client()
    try:
        response = await client.delete(f"/api/v2/changes/{change_id}")
        if response.status_code == 204:
            return {"success": True, "message": "Change deleted successfully"}
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to delete change", e)


@conditional_tool()
async def filter_changes(
    query: str,
    page: int = 1,
    per_page: int = 30,
    sort: Optional[str] = None,
    order_by: Optional[str] = None,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Search changes using Freshservice's filter query syntax.

    Query examples:
        "status:3"                              — Awaiting Approval
        "priority:4 AND risk:3"                 — Urgent + High risk
        "agent_id:12345"                        — assigned to agent
        "change_type:4 AND status:1"            — Emergency + Open
        "created_at:>'2024-01-01'"              — created after date

    Status values: 1=Open, 2=Planning, 3=Awaiting Approval,
    4=Pending Release, 5=Pending Review, 6=Closed.
    Operators: AND, OR, >, <, :  (colon = equals).

    Args:
        query: Filter query string
        page: Page number (default: 1)
        per_page: Items per page (1-100, default: 30)
        sort: Sort field
        order_by: 'asc' or 'desc'
        workspace_id: Optional workspace ID filter"""
    return await get_changes(
        page=page,
        per_page=per_page,
        query=query,
        sort=sort,
        order_by=order_by,
        workspace_id=workspace_id,
    )


@conditional_tool()
@cached_response()
async def list_change_fields() -> Dict[str, Any]:
    """Get the raw change form field definitions from Freshservice (cached).

    Returns field names, types, choices, and validation rules for every
    field on the change form.  Useful for discovering custom fields."""
    client = get_client()
    try:
        response = await client.get("/api/v2/change_form_fields")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to fetch change fields", e)


@conditional_tool()
async def move_change(change_id: int, workspace_id: int) -> Dict[str, Any]:
    """Move a change to a different workspace by workspace_id."""
    client = get_client()
    try:
        response = await client.put(
            f"/api/v2/changes/{change_id}/move_workspace",
            json={"workspace_id": workspace_id},
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to move change", e)


# ============================================================
# Approvals
# ============================================================


@conditional_tool()
async def create_change_approval_group(
    change_id: int,
    name: str,
    approver_ids: List[int],
    approval_type: str = "everyone",
) -> Dict[str, Any]:
    """Create an approval group on a change to gate its progression.

    Args:
        change_id: The change requiring approval
        name: Display name for this approval group
        approver_ids: Agent IDs who can approve
        approval_type: 'everyone' (all must approve) or 'any' (one suffices)"""
    client = get_client()
    try:
        response = await client.post(
            f"/api/v2/changes/{change_id}/approval_groups",
            json={"name": name, "approver_ids": approver_ids, "approval_type": approval_type},
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to create approval group", e)


@conditional_tool()
async def update_change_approval_group(
    change_id: int,
    group_id: int,
    name: Optional[str] = None,
    approver_ids: Optional[List[int]] = None,
    approval_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Update the name, approvers, or approval type of an approval group."""
    data: Dict[str, Any] = {}
    if name is not None:
        data["name"] = name
    if approver_ids is not None:
        data["approver_ids"] = approver_ids
    if approval_type is not None:
        data["approval_type"] = approval_type

    client = get_client()
    try:
        response = await client.put(
            f"/api/v2/changes/{change_id}/approval_groups/{group_id}",
            json=data,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to update approval group", e)


@conditional_tool()
async def cancel_change_approval_group(change_id: int, group_id: int) -> Dict[str, Any]:
    """Cancel an entire approval group, removing it from the approval flow."""
    client = get_client()
    try:
        response = await client.put(
            f"/api/v2/changes/{change_id}/approval_groups/{group_id}/cancel"
        )
        response.raise_for_status()
        return {"success": True, "message": "Approval group cancelled successfully"}
    except Exception as e:
        return api_error("Failed to cancel approval group", e)


@conditional_tool()
async def update_approval_chain_rule_change(
    change_id: int,
    approval_chain_type: str = "parallel",
) -> Dict[str, Any]:
    """Set whether approval groups run in parallel or sequentially.

    Args:
        change_id: The change to update
        approval_chain_type: 'parallel' (all groups at once) or
                             'sequential' (one after another)"""
    if approval_chain_type not in ("parallel", "sequential"):
        return {"error": "approval_chain_type must be 'parallel' or 'sequential'"}

    client = get_client()
    try:
        response = await client.put(
            f"/api/v2/changes/{change_id}/approval_chain",
            json={"approval_chain_type": approval_chain_type},
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to update approval chain", e)


@conditional_tool()
async def list_change_approval_groups(
    change_id: int,
    page: int = 1,
    per_page: int = 30,
) -> Dict[str, Any]:
    """List all approval groups configured on a change.

    Each group includes its approvers, approval_type, and current status.

    Args:
        change_id: The change to inspect
        page: Page number (default: 1)
        per_page: Items per page (1-100, default: 30)"""
    if page < 1:
        return {"error": "Page number must be greater than 0"}
    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    client = get_client()
    try:
        response = await client.get(
            f"/api/v2/changes/{change_id}/approval_groups",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()

        pagination_info = parse_link_header(response.headers.get("Link", ""))
        return {
            "approval_groups": response.json(),
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "has_more": pagination_info.get("next") is not None,
            },
        }
    except Exception as e:
        return api_error("Failed to fetch approval groups", e)


@conditional_tool()
async def view_change_approval(change_id: int, approval_id: int) -> Dict[str, Any]:
    """View a single approval record by its approval_id within a change."""
    client = get_client()
    try:
        response = await client.get(
            f"/api/v2/changes/{change_id}/approvals/{approval_id}"
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to fetch approval", e)


@conditional_tool()
async def list_change_approvals(
    change_id: int,
    page: int = 1,
    per_page: int = 30,
) -> Dict[str, Any]:
    """List all individual approval records for a change.

    Returns each approver's decision (requested, approved, rejected)
    across all approval groups.

    Args:
        change_id: The change to inspect
        page: Page number (default: 1)
        per_page: Items per page (1-100, default: 30)"""
    if page < 1:
        return {"error": "Page number must be greater than 0"}
    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    client = get_client()
    try:
        response = await client.get(
            f"/api/v2/changes/{change_id}/approvals",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()

        pagination_info = parse_link_header(response.headers.get("Link", ""))
        return {
            "approvals": response.json(),
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "has_more": pagination_info.get("next") is not None,
            },
        }
    except Exception as e:
        return api_error("Failed to fetch approvals", e)


@conditional_tool()
async def send_change_approval_reminder(
    change_id: int,
    approval_id: int,
) -> Dict[str, Any]:
    """Re-send the approval notification email to a pending approver."""
    client = get_client()
    try:
        response = await client.put(
            f"/api/v2/changes/{change_id}/approvals/{approval_id}/resend_approval"
        )
        response.raise_for_status()
        return {"success": True, "message": "Reminder sent successfully"}
    except Exception as e:
        return api_error("Failed to send approval reminder", e)


@conditional_tool()
async def cancel_change_approval(
    change_id: int,
    approval_id: int,
) -> Dict[str, Any]:
    """Cancel a single pending approval, removing it from the approval flow."""
    client = get_client()
    try:
        response = await client.put(
            f"/api/v2/changes/{change_id}/approvals/{approval_id}/cancel"
        )
        response.raise_for_status()
        return {"success": True, "message": "Approval cancelled successfully"}
    except Exception as e:
        return api_error("Failed to cancel approval", e)


# ============================================================
# Notes
# ============================================================


@conditional_tool()
async def create_change_note(change_id: int, body: str) -> Dict[str, Any]:
    """Add an internal note to a change for record-keeping or communication."""
    client = get_client()
    try:
        response = await client.post(
            f"/api/v2/changes/{change_id}/notes",
            json={"body": body},
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to create change note", e)


@conditional_tool()
async def view_change_note(change_id: int, note_id: int) -> Dict[str, Any]:
    """Fetch a single note by its note_id within a change."""
    client = get_client()
    try:
        response = await client.get(f"/api/v2/changes/{change_id}/notes/{note_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to fetch change note", e)


@conditional_tool()
async def list_change_notes(
    change_id: int,
    page: int = 1,
    per_page: int = 30,
) -> Dict[str, Any]:
    """List all notes attached to a change in chronological order.

    Args:
        change_id: The change to inspect
        page: Page number (default: 1)
        per_page: Items per page (1-100, default: 30)"""
    if page < 1:
        return {"error": "Page number must be greater than 0"}
    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    client = get_client()
    try:
        response = await client.get(
            f"/api/v2/changes/{change_id}/notes",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()

        pagination_info = parse_link_header(response.headers.get("Link", ""))
        return {
            "notes": response.json(),
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "has_more": pagination_info.get("next") is not None,
            },
        }
    except Exception as e:
        return api_error("Failed to fetch change notes", e)


@conditional_tool()
async def update_change_note(
    change_id: int,
    note_id: int,
    body: str,
) -> Dict[str, Any]:
    """Edit the body of an existing change note."""
    client = get_client()
    try:
        response = await client.put(
            f"/api/v2/changes/{change_id}/notes/{note_id}",
            json={"body": body},
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to update change note", e)


@conditional_tool()
async def delete_change_note(change_id: int, note_id: int) -> Dict[str, Any]:
    """Permanently delete a note from a change."""
    client = get_client()
    try:
        response = await client.delete(f"/api/v2/changes/{change_id}/notes/{note_id}")
        if response.status_code == 204:
            return {"success": True, "message": "Note deleted successfully"}
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to delete change note", e)


# ============================================================
# Tasks
# ============================================================


@conditional_tool()
async def get_change_tasks(
    change_id: int,
    page: int = 1,
    per_page: int = 30,
) -> Dict[str, Any]:
    """List all tasks (sub-items) attached to a change.

    Tasks track individual work items within a change, each with its
    own status, assignee, and due date.

    Args:
        change_id: The change to inspect
        page: Page number (default: 1)
        per_page: Items per page (1-100, default: 30)"""
    if page < 1:
        return {"error": "Page number must be greater than 0"}
    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    client = get_client()
    try:
        response = await client.get(
            f"/api/v2/changes/{change_id}/tasks",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()

        pagination_info = parse_link_header(response.headers.get("Link", ""))
        return {
            "tasks": response.json(),
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "has_more": pagination_info.get("next") is not None,
            },
        }
    except Exception as e:
        return api_error("Failed to fetch change tasks", e)


@conditional_tool()
async def create_change_task(
    change_id: int,
    title: str,
    description: str,
    status: int = 1,
    priority: int = 1,
    assigned_to_id: Optional[int] = None,
    group_id: Optional[int] = None,
    due_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a sub-task within a change.

    Args:
        change_id: Parent change
        title: Task title
        description: Task details
        status: 1=Open, 2=In Progress, 3=Completed
        priority: 1=Low, 2=Medium, 3=High
        assigned_to_id: Agent responsible for this task
        group_id: Agent group responsible
        due_date: Due date in ISO format"""
    data: Dict[str, Any] = {
        "title": title,
        "description": description,
        "status": status,
        "priority": priority,
    }
    if assigned_to_id:
        data["assigned_to_id"] = assigned_to_id
    if group_id:
        data["group_id"] = group_id
    if due_date:
        data["due_date"] = due_date

    client = get_client()
    try:
        response = await client.post(
            f"/api/v2/changes/{change_id}/tasks",
            json=data,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to create change task", e)


@conditional_tool()
async def view_change_task(change_id: int, task_id: int) -> Dict[str, Any]:
    """Fetch a single task by its task_id within a change."""
    client = get_client()
    try:
        response = await client.get(f"/api/v2/changes/{change_id}/tasks/{task_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to fetch change task", e)


@conditional_tool()
async def update_change_task(
    change_id: int,
    task_id: int,
    task_fields: Dict[str, Any],
) -> Dict[str, Any]:
    """Update fields on a change task (status, title, assignee, etc.)."""
    client = get_client()
    try:
        response = await client.put(
            f"/api/v2/changes/{change_id}/tasks/{task_id}",
            json=task_fields,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to update change task", e)


@conditional_tool()
async def delete_change_task(change_id: int, task_id: int) -> Dict[str, Any]:
    """Permanently delete a task from a change."""
    client = get_client()
    try:
        response = await client.delete(f"/api/v2/changes/{change_id}/tasks/{task_id}")
        if response.status_code == 204:
            return {"success": True, "message": "Task deleted successfully"}
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to delete change task", e)


# ============================================================
# Time Entries
# ============================================================


@conditional_tool()
async def create_change_time_entry(
    change_id: int,
    time_spent: str,
    note: str,
    agent_id: int,
    executed_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a time entry for a change.

    Args:
        change_id: The ID of the change
        time_spent: Time spent in format "hh:mm" (e.g., "02:30")
        note: Description of the work done
        agent_id: ID of the agent who performed the work
        executed_at: When the work was done (ISO format)
    """
    data: Dict[str, Any] = {
        "time_spent": time_spent,
        "note": note,
        "agent_id": agent_id,
    }
    if executed_at:
        data["executed_at"] = executed_at

    client = get_client()
    try:
        response = await client.post(
            f"/api/v2/changes/{change_id}/time_entries",
            json=data,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to create time entry", e)


@conditional_tool()
async def view_change_time_entry(
    change_id: int,
    time_entry_id: int,
) -> Dict[str, Any]:
    """Fetch a single time entry by its time_entry_id within a change."""
    client = get_client()
    try:
        response = await client.get(
            f"/api/v2/changes/{change_id}/time_entries/{time_entry_id}"
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to fetch time entry", e)


@conditional_tool()
async def list_change_time_entries(
    change_id: int,
    page: int = 1,
    per_page: int = 30,
) -> Dict[str, Any]:
    """List all logged time entries for a change.

    Each entry includes agent, time_spent, note, and execution date.

    Args:
        change_id: The change to inspect
        page: Page number (default: 1)
        per_page: Items per page (1-100, default: 30)"""
    if page < 1:
        return {"error": "Page number must be greater than 0"}
    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    client = get_client()
    try:
        response = await client.get(
            f"/api/v2/changes/{change_id}/time_entries",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()

        pagination_info = parse_link_header(response.headers.get("Link", ""))
        return {
            "time_entries": response.json(),
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "has_more": pagination_info.get("next") is not None,
            },
        }
    except Exception as e:
        return api_error("Failed to fetch time entries", e)


@conditional_tool()
async def update_change_time_entry(
    change_id: int,
    time_entry_id: int,
    time_spent: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Edit the time_spent or note on an existing time entry."""
    data: Dict[str, Any] = {}
    if time_spent is not None:
        data["time_spent"] = time_spent
    if note is not None:
        data["note"] = note

    client = get_client()
    try:
        response = await client.put(
            f"/api/v2/changes/{change_id}/time_entries/{time_entry_id}",
            json=data,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to update time entry", e)


@conditional_tool()
async def delete_change_time_entry(
    change_id: int,
    time_entry_id: int,
) -> Dict[str, Any]:
    """Permanently delete a time entry from a change."""
    client = get_client()
    try:
        response = await client.delete(
            f"/api/v2/changes/{change_id}/time_entries/{time_entry_id}"
        )
        if response.status_code == 204:
            return {"success": True, "message": "Time entry deleted successfully"}
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to delete time entry", e)
