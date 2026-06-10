"""Requester tools."""

import urllib.parse
from typing import Any, Dict, List, Optional

from ..server import conditional_tool
from ..client import get_client, parse_link_header, cached_response


@conditional_tool()
async def create_requester(
    first_name: str,
    last_name: Optional[str] = None,
    job_title: Optional[str] = None,
    primary_email: Optional[str] = None,
    secondary_emails: Optional[List[str]] = None,
    work_phone_number: Optional[str] = None,
    mobile_phone_number: Optional[str] = None,
    department_ids: Optional[List[int]] = None,
    can_see_all_tickets_from_associated_departments: Optional[bool] = None,
    reporting_manager_id: Optional[int] = None,
    address: Optional[str] = None,
    time_zone: Optional[str] = None,
    time_format: Optional[str] = None,
    language: Optional[str] = None,
    location_id: Optional[int] = None,
    background_information: Optional[str] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a new requester (end-user who submits tickets).

    Requesters are distinct from agents — they cannot be assigned work.
    Requires first_name and at least one contact method (email or phone)."""
    if not isinstance(first_name, str) or not first_name.strip():
        return {"error": "'first_name' must be a non-empty string."}
    if not (primary_email or work_phone_number or mobile_phone_number):
        return {
            "error": "At least one of 'primary_email', 'work_phone_number', or 'mobile_phone_number' is required."
        }

    payload: Dict[str, Any] = {"first_name": first_name.strip()}
    optional_fields = {
        "last_name": last_name,
        "job_title": job_title,
        "primary_email": primary_email,
        "secondary_emails": secondary_emails,
        "work_phone_number": work_phone_number,
        "mobile_phone_number": mobile_phone_number,
        "department_ids": department_ids,
        "can_see_all_tickets_from_associated_departments": can_see_all_tickets_from_associated_departments,
        "reporting_manager_id": reporting_manager_id,
        "address": address,
        "time_zone": time_zone,
        "time_format": time_format,
        "language": language,
        "location_id": location_id,
        "background_information": background_information,
        "custom_fields": custom_fields,
    }
    payload.update({k: v for k, v in optional_fields.items() if v is not None})

    client = get_client()
    try:
        response = await client.post("/api/v2/requesters", json=payload)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"error": f"Failed to create requester: {e}"}


@conditional_tool()
async def get_all_requesters(
    page: int = 1,
    per_page: int = 30,
) -> Dict[str, Any]:
    """List all requesters in the Freshservice tenant with pagination.

    For targeted lookups, prefer filter_requesters with a query string."""
    if page < 1:
        return {"error": "Page number must be greater than 0"}
    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    client = get_client()
    try:
        response = await client.get(
            "/api/v2/requesters",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()

        data = response.json()
        requesters = data.get("requesters", [])
        pagination_info = parse_link_header(response.headers.get("Link", ""))

        return {
            "success": True,
            "requesters": requesters,
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "has_more": pagination_info.get("next") is not None,
            },
        }
    except Exception as e:
        return {"error": f"Failed to fetch requesters: {e}"}


@conditional_tool()
async def get_requester_by_id(requester_id: int) -> Dict[str, Any]:
    """Fetch a single requester's profile by their numeric requester_id.

    Returns name, email, phone, department, location, and custom fields."""
    client = get_client()
    try:
        response = await client.get(f"/api/v2/requesters/{requester_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch requester: {e}"}


@conditional_tool()
@cached_response()
async def list_all_requester_fields() -> Dict[str, Any]:
    """Get the raw requester form field definitions from Freshservice (cached).

    Returns field names, types, and choices for every field on the
    requester profile form.  Useful for discovering custom fields."""
    client = get_client()
    try:
        response = await client.get("/api/v2/requester_fields")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch requester fields: {e}"}


@conditional_tool()
async def update_requester(
    requester_id: int,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    job_title: Optional[str] = None,
    primary_email: Optional[str] = None,
    secondary_emails: Optional[List[str]] = None,
    work_phone_number: Optional[int] = None,
    mobile_phone_number: Optional[int] = None,
    department_ids: Optional[List[int]] = None,
    can_see_all_tickets_from_associated_departments: Optional[bool] = None,
    reporting_manager_id: Optional[int] = None,
    address: Optional[str] = None,
    time_zone: Optional[str] = None,
    time_format: Optional[str] = None,
    language: Optional[str] = None,
    location_id: Optional[int] = None,
    background_information: Optional[str] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Update profile fields on an existing requester.

    Only the fields you provide will be changed; others remain as-is."""
    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "job_title": job_title,
        "primary_email": primary_email,
        "secondary_emails": secondary_emails,
        "work_phone_number": work_phone_number,
        "mobile_phone_number": mobile_phone_number,
        "department_ids": department_ids,
        "can_see_all_tickets_from_associated_departments": can_see_all_tickets_from_associated_departments,
        "reporting_manager_id": reporting_manager_id,
        "address": address,
        "time_zone": time_zone,
        "time_format": time_format,
        "language": language,
        "location_id": location_id,
        "background_information": background_information,
        "custom_fields": custom_fields,
    }
    data = {k: v for k, v in payload.items() if v is not None}

    client = get_client()
    try:
        response = await client.put(f"/api/v2/requesters/{requester_id}", json=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to update requester: {e}"}


@conditional_tool()
async def filter_requesters(
    query: str,
    include_agents: bool = False,
) -> Dict[str, Any]:
    """Search requesters using Freshservice's query syntax.

    Query examples:
        "first_name:'Jane'"                — requesters named Jane
        "primary_email:'jane@example.com'" — exact email match
        "department_id:42"                 — requesters in department 42

    Args:
        query: Filter query string
        include_agents: If True, also return agents matching the query"""
    encoded_query = urllib.parse.quote(query)
    url = f"/api/v2/requesters?query={encoded_query}"
    if include_agents:
        url += "&include_agents=true"

    client = get_client()
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to filter requesters: {e}"}
