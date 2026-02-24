"""Canned response tools."""

from typing import Any, Dict

from ..server import conditional_tool
from ..client import get_client, parse_link_header, cached_response


@conditional_tool()
async def get_all_canned_response(
    page: int = 1,
    per_page: int = 30,
) -> Dict[str, Any]:
    """List all canned responses (pre-written reply templates for tickets).

    Canned responses can be inserted into ticket replies to save time
    on common answers.  Use get_canned_response to fetch the full body.

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
            "/api/v2/canned_responses",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()

        pagination_info = parse_link_header(response.headers.get("Link", ""))
        return {
            "canned_responses": response.json(),
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "has_more": pagination_info.get("next") is not None,
            },
        }
    except Exception as e:
        return {"error": f"Failed to fetch canned responses: {e}"}


@conditional_tool()
async def get_canned_response(canned_response_id: int) -> Dict[str, Any]:
    """Fetch the full body of a single canned response by its ID.

    Returns the title, HTML body, and folder information."""
    client = get_client()
    try:
        response = await client.get(f"/api/v2/canned_responses/{canned_response_id}")
        response.raise_for_status()
        if response.content:
            return response.json()
        return {"error": "No content returned for the requested canned response."}
    except Exception as e:
        return {"error": f"Failed to fetch canned response: {e}"}


@conditional_tool()
@cached_response()
async def list_all_canned_response_folder(
    page: int = 1,
    per_page: int = 30,
) -> Dict[str, Any]:
    """List all folders that organize canned responses (cached).

    Folders group canned responses by topic or team.  Use
    list_canned_response_folder to get details on a specific folder.

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
            "/api/v2/canned_response_folders",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()

        pagination_info = parse_link_header(response.headers.get("Link", ""))
        return {
            "canned_response_folders": response.json(),
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "has_more": pagination_info.get("next") is not None,
            },
        }
    except Exception as e:
        return {"error": f"Failed to fetch canned response folders: {e}"}


@conditional_tool()
async def list_canned_response_folder(folder_id: int) -> Dict[str, Any]:
    """Fetch a single canned response folder by its folder_id.

    Returns the folder name, description, and contained response IDs."""
    client = get_client()
    try:
        response = await client.get(f"/api/v2/canned_response_folders/{folder_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch canned response folder: {e}"}
