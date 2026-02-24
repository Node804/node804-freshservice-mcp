"""Product tools."""

from typing import Any, Dict, Optional, Union

from ..server import conditional_tool
from ..client import get_client, parse_link_header


@conditional_tool()
async def get_all_products(
    page: Optional[int] = 1,
    per_page: Optional[int] = 30,
) -> Dict[str, Any]:
    """List all products (hardware/software tracked as assets) with pagination.

    Products define asset types that can be associated with tickets
    for inventory and procurement tracking."""
    if page < 1:
        return {"error": "Page number must be greater than 0"}
    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    client = get_client()
    try:
        response = await client.get(
            "/api/v2/products",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()

        data = response.json()
        products = data.get("products", [])
        pagination_info = parse_link_header(response.headers.get("Link", ""))
        next_page = pagination_info.get("next")

        return {
            "success": True,
            "products": products,
            "pagination": {
                "current_page": page,
                "next_page": next_page,
                "has_next": bool(next_page),
                "per_page": per_page,
            },
        }
    except Exception as e:
        return {"error": f"Failed to fetch products: {e}"}


@conditional_tool()
async def get_product_by_id(product_id: int) -> Dict[str, Any]:
    """Fetch a single product by its numeric product_id.

    Returns name, asset_type_id, manufacturer, status, and description."""
    client = get_client()
    try:
        response = await client.get(f"/api/v2/products/{product_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch product: {e}"}


@conditional_tool()
async def create_product(
    name: str,
    asset_type_id: int,
    manufacturer: Optional[str] = None,
    status: Optional[Union[str, int]] = None,
    mode_of_procurement: Optional[str] = None,
    depreciation_type_id: Optional[int] = None,
    description: Optional[str] = None,
    description_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new product for asset tracking.

    Args:
        name: Product name
        asset_type_id: ID of the asset type this product belongs to
        status: "In Production" (1), "In Pipeline" (2), or "Retired" (3)
        mode_of_procurement: e.g. "Buy", "Lease"
        description: HTML description
        description_text: Plain-text description"""
    allowed_statuses = {
        "In Production": "In Production",
        "In Pipeline": "In Pipeline",
        "Retired": "Retired",
        1: "In Production",
        2: "In Pipeline",
        3: "Retired",
    }

    if status is not None:
        if status not in allowed_statuses:
            return {
                "error": (
                    "Invalid 'status'. Must be one of: "
                    '"In Production" (1), "In Pipeline" (2), "Retired" (3)'
                )
            }
        status = allowed_statuses[status]

    payload: Dict[str, Any] = {"name": name, "asset_type_id": asset_type_id}
    if manufacturer:
        payload["manufacturer"] = manufacturer
    if status:
        payload["status"] = status
    if mode_of_procurement:
        payload["mode_of_procurement"] = mode_of_procurement
    if depreciation_type_id:
        payload["depreciation_type_id"] = depreciation_type_id
    if description:
        payload["description"] = description
    if description_text:
        payload["description_text"] = description_text

    client = get_client()
    try:
        response = await client.post("/api/v2/products", json=payload)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"error": f"Failed to create product: {e}"}


@conditional_tool()
async def update_product(
    product_id: int,
    name: str,
    asset_type_id: int,
    manufacturer: Optional[str] = None,
    status: Optional[Union[str, int]] = None,
    mode_of_procurement: Optional[str] = None,
    depreciation_type_id: Optional[int] = None,
    description: Optional[str] = None,
    description_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an existing product's details.

    Args:
        product_id: The product to update
        name: Product name (required for update)
        asset_type_id: Asset type ID (required for update)
        status: "In Production" (1), "In Pipeline" (2), or "Retired" (3)"""
    allowed_statuses = {
        "In Production": "In Production",
        "In Pipeline": "In Pipeline",
        "Retired": "Retired",
        1: "In Production",
        2: "In Pipeline",
        3: "Retired",
    }

    if status is not None:
        if status not in allowed_statuses:
            return {
                "error": (
                    "Invalid 'status'. Must be one of: "
                    '"In Production" (1), "In Pipeline" (2), "Retired" (3)'
                )
            }
        status = allowed_statuses[status]

    payload: Dict[str, Any] = {"name": name, "asset_type_id": asset_type_id}
    if manufacturer:
        payload["manufacturer"] = manufacturer
    if status:
        payload["status"] = status
    if mode_of_procurement:
        payload["mode_of_procurement"] = mode_of_procurement
    if depreciation_type_id:
        payload["depreciation_type_id"] = depreciation_type_id
    if description:
        payload["description"] = description
    if description_text:
        payload["description_text"] = description_text

    client = get_client()
    try:
        response = await client.put(f"/api/v2/products/{product_id}", json=payload)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"error": f"Failed to update product: {e}"}
