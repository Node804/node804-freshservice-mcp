"""Agent group and requester group tools."""

from typing import Any, Dict, Optional

from ..server import conditional_tool
from ..client import get_client, parse_link_header, api_error
from ..models import GroupCreate


# --- Agent Groups ---


@conditional_tool()
async def get_all_agent_groups(
    page: int = 1,
    per_page: int = 30,
) -> Dict[str, Any]:
    """List all agent groups (teams that tickets/changes can be assigned to).

    Agent groups organize IT staff for routing and workload management.

    Args:
        page: Page number (default: 1)
        per_page: Items per page (1-100, default: 30)"""
    if page < 1:
        return {"error": "Page number must be greater than 0"}
    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    client = get_client()
    try:
        response = await client.get(
            "/api/v2/groups",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()

        pagination_info = parse_link_header(response.headers.get("Link", ""))
        return {
            "groups": response.json(),
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "has_more": pagination_info.get("next") is not None,
            },
        }
    except Exception as e:
        return api_error("Failed to fetch agent groups", e)


@conditional_tool()
async def get_agent_group_by_id(group_id: int) -> Dict[str, Any]:
    """Fetch a single agent group by its numeric group_id.

    Returns group name, description, member agent IDs, and settings."""
    client = get_client()
    try:
        response = await client.get(f"/api/v2/groups/{group_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to fetch agent group", e)


@conditional_tool()
async def create_group(group_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new agent group.  The 'name' key is required in group_data."""
    if "name" not in group_data:
        return {"error": "Field 'name' is required to create a group."}

    client = get_client()
    try:
        response = await client.post("/api/v2/groups", json=group_data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to create group", e)


@conditional_tool()
async def update_group(
    group_id: int,
    group_fields: Dict[str, Any],
) -> Dict[str, Any]:
    """Update an existing agent group's name, description, or members."""
    try:
        validated_fields = GroupCreate(**group_fields)
        group_data = validated_fields.model_dump(exclude_none=True)
    except Exception as e:
        return api_error("Validation error", e)

    client = get_client()
    try:
        response = await client.put(f"/api/v2/groups/{group_id}", json=group_data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to update group", e)


# --- Requester Groups ---


@conditional_tool()
async def get_all_requester_groups(
    page: Optional[int] = 1,
    per_page: Optional[int] = 30,
) -> Dict[str, Any]:
    """List all requester groups (end-user groupings for access/visibility rules)."""
    if page < 1:
        return {"error": "Page number must be greater than 0"}
    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    client = get_client()
    try:
        response = await client.get(
            "/api/v2/requester_groups",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()

        pagination_info = parse_link_header(response.headers.get("Link", ""))
        return {
            "success": True,
            "requester_groups": response.json(),
            "pagination": {
                "current_page": page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "per_page": per_page,
            },
        }
    except Exception as e:
        return api_error("Failed to fetch requester groups", e)


@conditional_tool()
async def get_requester_groups_by_id(requester_group_id: int) -> Dict[str, Any]:
    """Fetch a single requester group by its ID."""
    client = get_client()
    try:
        response = await client.get(f"/api/v2/requester_groups/{requester_group_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to fetch requester group", e)


@conditional_tool()
async def create_requester_group(
    name: str,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new requester group with a name and optional description."""
    group_data: Dict[str, Any] = {"name": name}
    if description:
        group_data["description"] = description

    client = get_client()
    try:
        response = await client.post("/api/v2/requester_groups", json=group_data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to create requester group", e)


@conditional_tool()
async def update_requester_group(
    requester_group_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Update a requester group's name or description."""
    group_data: Dict[str, Any] = {}
    if name:
        group_data["name"] = name
    if description:
        group_data["description"] = description

    if not group_data:
        return {"error": "At least one field (name or description) must be provided to update."}

    client = get_client()
    try:
        response = await client.put(
            f"/api/v2/requester_groups/{requester_group_id}",
            json=group_data,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to update requester group", e)


@conditional_tool()
async def list_requester_group_members(
    group_id: int,
    page: int = 1,
    per_page: int = 30,
) -> Dict[str, Any]:
    """List all requesters who belong to a specific requester group.

    Args:
        group_id: The requester group to inspect
        page: Page number (default: 1)
        per_page: Items per page (1-100, default: 30)"""
    if page < 1:
        return {"error": "Page number must be greater than 0"}
    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    client = get_client()
    try:
        response = await client.get(
            f"/api/v2/requester_groups/{group_id}/members",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()

        pagination_info = parse_link_header(response.headers.get("Link", ""))
        return {
            "members": response.json(),
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "has_more": pagination_info.get("next") is not None,
            },
        }
    except Exception as e:
        return api_error("Failed to fetch requester group members", e)


@conditional_tool()
async def add_requester_to_group(
    group_id: int,
    requester_id: int,
) -> Dict[str, Any]:
    """Add a requester to a manual requester group by requester_id.

    Only works for groups with manual membership (not rule-based)."""
    client = get_client()
    try:
        response = await client.post(
            f"/api/v2/requester_groups/{group_id}/members/{requester_id}"
        )
        response.raise_for_status()
        return {"success": True, "message": f"Requester {requester_id} added to group {group_id}."}
    except Exception as e:
        return api_error("Failed to add requester to group", e)
