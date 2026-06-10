"""Service catalog tools."""

from typing import Any, Dict, List, Optional

from ..server import conditional_tool
from ..client import get_client, parse_link_header, api_error


@conditional_tool()
async def list_service_items(
    page: Optional[int] = 1,
    per_page: Optional[int] = 30,
    max_pages: int = 3,
) -> Dict[str, Any]:
    """List items available in the Freshservice service catalog.

    Service catalog items are predefined offerings that end-users can
    request (e.g. "New Laptop", "VPN Access").  Use create_service_request
    to place a request for a specific catalog item.

    Args:
        page: Starting page number (default: 1)
        per_page: Items per page (1-100, default: 30)
        max_pages: Max pages to auto-paginate (default: 3)"""
    if page < 1:
        return {"error": "Page number must be greater than 0"}
    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    client = get_client()
    all_items: List[Dict[str, Any]] = []
    current_page = page
    pages_fetched = 0

    try:
        while pages_fetched < max_pages:
            response = await client.get(
                "/api/v2/service_catalog/items",
                params={"page": current_page, "per_page": per_page},
            )
            response.raise_for_status()

            data = response.json()
            all_items.append(data)
            pages_fetched += 1

            pagination_info = parse_link_header(response.headers.get("Link", ""))
            if not pagination_info.get("next"):
                break
            current_page = pagination_info["next"]

        return {
            "success": True,
            "items": all_items,
            "pagination": {
                "starting_page": page,
                "per_page": per_page,
                "last_fetched_page": current_page,
                "pages_fetched": pages_fetched,
                "capped": pages_fetched >= max_pages,
            },
        }
    except Exception as e:
        return api_error("Failed to fetch service items", e)


@conditional_tool()
async def get_requested_items(ticket_id: int) -> Dict[str, Any]:
    """Fetch the catalog items attached to a service-request ticket.

    Only works for tickets of type "Service Request".  Returns the
    item details, quantity, and fulfillment status for each requested item."""
    client = get_client()

    # Step 1: Check if the ticket is a service request
    try:
        response = await client.get(f"/api/v2/tickets/{ticket_id}")
        response.raise_for_status()
        ticket_data = response.json()

        if ticket_data.get("ticket", {}).get("type") != "Service Request":
            return {"error": "Requested items can only be fetched for service requests"}
    except Exception as e:
        return api_error("Failed to fetch ticket", e)

    # Step 2: Fetch the requested items
    try:
        response = await client.get(f"/api/v2/tickets/{ticket_id}/requested_items")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to fetch requested items", e)


@conditional_tool()
async def create_service_request(
    display_id: int,
    email: str,
    requested_for: Optional[str] = None,
    quantity: int = 1,
) -> Dict[str, Any]:
    """Place a service request for a catalog item on behalf of a user.

    Creates a new "Service Request" ticket linked to the catalog item.

    Args:
        display_id: The catalog item's display ID (visible in the portal)
        email: Email of the requester placing the request
        requested_for: Email of the person the request is for (if different)
        quantity: Number of items requested (default: 1)"""
    if not isinstance(quantity, int) or quantity <= 0:
        return {"error": "Quantity must be a positive integer."}
    if requested_for and "@" not in requested_for:
        return {"error": "requested_for must be a valid email address."}

    payload: Dict[str, Any] = {"email": email, "quantity": quantity}
    if requested_for:
        payload["requested_for"] = requested_for

    client = get_client()
    try:
        response = await client.post(
            f"/api/v2/service_catalog/items/{display_id}/place_request",
            json=payload,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return api_error("Failed to place service request", e)
