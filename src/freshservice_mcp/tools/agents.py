"""Agent tools."""

import urllib.parse
from typing import Any, Dict, List, Optional

from ..server import conditional_tool
from ..client import get_client, parse_link_header, cached_response
from ..models import AgentInput


@conditional_tool()
@cached_response()
async def get_current_agent() -> Dict[str, Any]:
    """Get the agent profile for the authenticated API key.

    Returns the current user's agent_id, name, email, groups, roles, and other
    profile data.  Cached for 1 hour since this never changes mid-session.
    Useful as the first step for any "my tickets" / "my changes" query.
    """
    client = get_client()
    try:
        response = await client.get("/api/v2/agents/me")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch current agent: {e}"}


@conditional_tool()
async def create_agent(
    first_name: str,
    email: Optional[str] = None,
    last_name: Optional[str] = None,
    occasional: Optional[bool] = False,
    job_title: Optional[str] = None,
    work_phone_number: Optional[int] = None,
    mobile_phone_number: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a new agent (IT staff member) in Freshservice.

    Agents can be assigned tickets and changes.  At minimum, first_name
    is required.  Set occasional=True for part-time/occasional agents."""
    data = AgentInput(
        first_name=first_name,
        last_name=last_name,
        occasional=occasional,
        job_title=job_title,
        email=email,
        work_phone_number=work_phone_number,
        mobile_phone_number=mobile_phone_number,
    ).dict(exclude_none=True)

    client = get_client()
    try:
        response = await client.post("/api/v2/agents", json=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to create agent: {e}"}


@conditional_tool()
async def get_agent(agent_id: int) -> Dict[str, Any]:
    """Fetch a single agent's profile by their numeric agent_id.

    Returns name, email, roles, groups, department, and other profile data."""
    client = get_client()
    try:
        response = await client.get(f"/api/v2/agents/{agent_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch agent: {e}"}


@conditional_tool()
async def get_all_agents(
    page: int = 1,
    per_page: int = 30,
) -> Dict[str, Any]:
    """List all agents in the Freshservice tenant with pagination.

    For targeted lookups, prefer filter_agents with a query string."""
    if page < 1:
        return {"error": "Page number must be greater than 0"}
    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    client = get_client()
    try:
        response = await client.get(
            "/api/v2/agents",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()

        data = response.json()
        agents = data.get("agents", [])
        pagination_info = parse_link_header(response.headers.get("Link", ""))

        return {
            "success": True,
            "agents": agents,
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "has_more": pagination_info.get("next") is not None,
            },
        }
    except Exception as e:
        return {"error": f"Failed to fetch agents: {e}"}


@conditional_tool()
async def filter_agents(
    query: str,
    max_pages: int = 3,
) -> Dict[str, Any]:
    """Search agents using Freshservice's filter query syntax.

    Query examples:
        "first_name:John"                  — agents named John
        "email:john@example.com"           — exact email match
        "department_id:42"                  — agents in department 42
        "active:true"                      — only active agents

    Args:
        query: Filter query string
        max_pages: Max pages to auto-paginate (default: 3)"""
    encoded_query = urllib.parse.quote(f'"{query}"')
    client = get_client()
    all_agents: List[Dict[str, Any]] = []
    page = 1
    pages_fetched = 0

    try:
        while pages_fetched < max_pages:
            response = await client.get(
                f"/api/v2/agents?query={encoded_query}&page={page}"
            )
            response.raise_for_status()

            data = response.json()
            all_agents.extend(data.get("agents", []))
            pages_fetched += 1

            pagination_info = parse_link_header(response.headers.get("Link", ""))
            if not pagination_info.get("next"):
                break
            page = pagination_info["next"]

        return {
            "agents": all_agents,
            "total_fetched": len(all_agents),
            "pages_fetched": pages_fetched,
            "capped": pages_fetched >= max_pages,
        }
    except Exception as e:
        return {"error": f"Failed to filter agents: {e}"}


@conditional_tool()
async def update_agent(
    agent_id: int,
    occasional: Optional[bool] = None,
    email: Optional[str] = None,
    department_ids: Optional[List[int]] = None,
    can_see_all_tickets_from_associated_departments: Optional[bool] = None,
    reporting_manager_id: Optional[int] = None,
    address: Optional[str] = None,
    time_zone: Optional[str] = None,
    time_format: Optional[str] = None,
    language: Optional[str] = None,
    location_id: Optional[int] = None,
    background_information: Optional[str] = None,
    scoreboard_level_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Update profile fields on an existing agent.

    Only the fields you provide will be changed; others remain as-is."""
    payload = {
        "occasional": occasional,
        "email": email,
        "department_ids": department_ids,
        "can_see_all_tickets_from_associated_departments": can_see_all_tickets_from_associated_departments,
        "reporting_manager_id": reporting_manager_id,
        "address": address,
        "time_zone": time_zone,
        "time_format": time_format,
        "language": language,
        "location_id": location_id,
        "background_information": background_information,
        "scoreboard_level_id": scoreboard_level_id,
    }
    data = {k: v for k, v in payload.items() if v is not None}

    client = get_client()
    try:
        response = await client.put(f"/api/v2/agents/{agent_id}", json=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to update agent: {e}"}


@conditional_tool()
@cached_response()
async def get_agent_fields() -> Dict[str, Any]:
    """Get the raw agent form field definitions from Freshservice (cached).

    Returns field names, types, and choices for every field on the
    agent profile form.  Useful for discovering custom fields."""
    client = get_client()
    try:
        response = await client.get("/api/v2/agent_fields")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch agent fields: {e}"}
