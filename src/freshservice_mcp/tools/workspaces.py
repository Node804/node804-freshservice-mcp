"""Workspace tools."""

from typing import Any, Dict

from ..server import conditional_tool
from ..client import get_client, cached_response


@conditional_tool()
@cached_response()
async def list_all_workspaces() -> Dict[str, Any]:
    """List all workspaces in the Freshservice tenant (cached).

    Workspaces partition tickets, changes, and other data for
    multi-department or multi-location organizations.  The workspace_id
    is used to filter results in other tools."""
    client = get_client()
    try:
        response = await client.get("/api/v2/workspaces")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch workspaces: {e}"}


@conditional_tool()
async def get_workspace(workspace_id: int) -> Dict[str, Any]:
    """Fetch a single workspace by its numeric workspace_id.

    Returns the workspace name, description, and configuration."""
    client = get_client()
    try:
        response = await client.get(f"/api/v2/workspaces/{workspace_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch workspace: {e}"}
