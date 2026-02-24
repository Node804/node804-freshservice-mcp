"""Solutions/Knowledge Base tools (categories, folders, articles)."""

from typing import Any, Dict, List, Optional

from ..server import conditional_tool
from ..client import get_client, parse_link_header, cached_response


# --- Categories ---


@conditional_tool()
@cached_response()
async def get_all_solution_category(
    page: int = 1,
    per_page: int = 30,
) -> Dict[str, Any]:
    """List all top-level knowledge base categories (cached).

    The KB is organized as: Categories → Folders → Articles.
    Start here to browse, then use get_list_of_solution_folder to
    drill into a category, and get_list_of_solution_article for articles.

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
            "/api/v2/solutions/categories",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()

        pagination_info = parse_link_header(response.headers.get("Link", ""))
        return {
            "categories": response.json(),
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "has_more": pagination_info.get("next") is not None,
            },
        }
    except Exception as e:
        return {"error": f"Failed to fetch solution categories: {e}"}


@conditional_tool()
async def get_solution_category(category_id: int) -> Dict[str, Any]:
    """Fetch a single KB category by its numeric category_id.

    Returns name, description, visibility, and folder count."""
    client = get_client()
    try:
        response = await client.get(f"/api/v2/solutions/categories/{category_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch solution category: {e}"}


@conditional_tool()
async def create_solution_category(
    name: str,
    description: Optional[str] = None,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a new top-level KB category to organize solution folders."""
    category_data = {"name": name}
    if description is not None:
        category_data["description"] = description
    if workspace_id is not None:
        category_data["workspace_id"] = workspace_id

    client = get_client()
    try:
        response = await client.post("/api/v2/solutions/categories", json=category_data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to create solution category: {e}"}


@conditional_tool()
async def update_solution_category(
    category_id: int,
    name: str,
    description: Optional[str] = None,
    workspace_id: Optional[int] = None,
    default_category: Optional[bool] = None,
) -> Dict[str, Any]:
    """Update a KB category's name, description, or default status."""
    category_data: Dict[str, Any] = {"name": name}
    if description is not None:
        category_data["description"] = description
    if workspace_id is not None:
        category_data["workspace_id"] = workspace_id
    if default_category is not None:
        category_data["default_category"] = default_category

    client = get_client()
    try:
        response = await client.put(
            f"/api/v2/solutions/categories/{category_id}",
            json=category_data,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to update solution category: {e}"}


# --- Folders ---


@conditional_tool()
async def get_list_of_solution_folder(
    category_id: int,
    page: int = 1,
    per_page: int = 30,
) -> Dict[str, Any]:
    """List all KB folders within a category.

    Folders sit between categories and articles in the KB hierarchy.
    Each folder has a visibility setting and department scope.

    Args:
        category_id: The parent category to browse
        page: Page number (default: 1)
        per_page: Items per page (1-100, default: 30)"""
    if page < 1:
        return {"error": "Page number must be greater than 0"}
    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    client = get_client()
    try:
        response = await client.get(
            "/api/v2/solutions/folders",
            params={"category_id": category_id, "page": page, "per_page": per_page},
        )
        response.raise_for_status()

        pagination_info = parse_link_header(response.headers.get("Link", ""))
        return {
            "folders": response.json(),
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "has_more": pagination_info.get("next") is not None,
            },
        }
    except Exception as e:
        return {"error": f"Failed to fetch solution folders: {e}"}


@conditional_tool()
async def get_solution_folder(folder_id: int) -> Dict[str, Any]:
    """Fetch a single KB folder by its numeric folder_id.

    Returns name, description, category_id, visibility, and article count."""
    client = get_client()
    try:
        response = await client.get(f"/api/v2/solutions/folders/{folder_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch solution folder: {e}"}


@conditional_tool()
async def create_solution_folder(
    name: str,
    category_id: int,
    department_ids: List[int],
    visibility: int = 4,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new KB folder within a category.

    Args:
        name: Folder name
        category_id: Parent category ID
        department_ids: Departments that can view this folder
        visibility: 1=All users, 2=Logged-in users, 3=Agents only,
                    4=Departments (default)
        description: Optional folder description"""
    if not department_ids:
        return {"error": "department_ids must be provided and cannot be empty."}

    payload: Dict[str, Any] = {
        "name": name,
        "category_id": category_id,
        "visibility": visibility,
        "department_ids": department_ids,
    }
    if description is not None:
        payload["description"] = description

    client = get_client()
    try:
        response = await client.post("/api/v2/solutions/folders", json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to create solution folder: {e}"}


@conditional_tool()
async def update_solution_folder(
    folder_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    visibility: Optional[int] = None,
) -> Dict[str, Any]:
    """Update a KB folder's name, description, or visibility."""
    payload = {
        "name": name,
        "description": description,
        "visibility": visibility,
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    client = get_client()
    try:
        response = await client.put(
            f"/api/v2/solutions/folders/{folder_id}",
            json=payload,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to update solution folder: {e}"}


# --- Articles ---


@conditional_tool()
async def get_list_of_solution_article(
    folder_id: int,
    page: int = 1,
    per_page: int = 30,
) -> Dict[str, Any]:
    """List all KB articles within a folder.

    Returns article titles, statuses, and metadata.  Use
    get_solution_article to fetch the full article body.

    Args:
        folder_id: The parent folder to browse
        page: Page number (default: 1)
        per_page: Items per page (1-100, default: 30)"""
    if page < 1:
        return {"error": "Page number must be greater than 0"}
    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    client = get_client()
    try:
        response = await client.get(
            "/api/v2/solutions/articles",
            params={"folder_id": folder_id, "page": page, "per_page": per_page},
        )
        response.raise_for_status()

        pagination_info = parse_link_header(response.headers.get("Link", ""))
        return {
            "articles": response.json(),
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "has_more": pagination_info.get("next") is not None,
            },
        }
    except Exception as e:
        return {"error": f"Failed to fetch solution articles: {e}"}


@conditional_tool()
async def get_solution_article(article_id: int) -> Dict[str, Any]:
    """Fetch the full KB article by its numeric article_id.

    Returns title, HTML body, status, tags, keywords, and folder info."""
    client = get_client()
    try:
        response = await client.get(f"/api/v2/solutions/articles/{article_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch solution article: {e}"}


@conditional_tool()
async def create_solution_article(
    title: str,
    description: str,
    folder_id: int,
    article_type: Optional[int] = 1,
    status: Optional[int] = 1,
    tags: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    review_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new KB article in a folder.

    Articles are created as drafts by default.  Use
    publish_solution_article or set status=2 to publish immediately.

    Args:
        title: Article title
        description: Article body (HTML supported)
        folder_id: Folder to create the article in
        article_type: 1=Permanent (default), 2=Workaround
        status: 1=Draft (default), 2=Published
        tags: Searchable tags
        keywords: SEO/search keywords
        review_date: Next review date (YYYY-MM-DD)"""
    article_data: Dict[str, Any] = {
        "title": title,
        "description": description,
        "folder_id": folder_id,
        "article_type": article_type,
        "status": status,
    }
    if tags is not None:
        article_data["tags"] = tags
    if keywords is not None:
        article_data["keywords"] = keywords
    if review_date is not None:
        article_data["review_date"] = review_date

    client = get_client()
    try:
        response = await client.post("/api/v2/solutions/articles", json=article_data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to create solution article: {e}"}


@conditional_tool()
async def update_solution_article(
    article_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    folder_id: Optional[int] = None,
    article_type: Optional[int] = None,
    status: Optional[int] = None,
    tags: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    review_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Update fields on an existing KB article.

    Only the fields you provide will be changed; others remain as-is."""
    update_data = {
        "title": title,
        "description": description,
        "folder_id": folder_id,
        "article_type": article_type,
        "status": status,
        "tags": tags,
        "keywords": keywords,
        "review_date": review_date,
    }
    update_data = {k: v for k, v in update_data.items() if v is not None}

    client = get_client()
    try:
        response = await client.put(
            f"/api/v2/solutions/articles/{article_id}",
            json=update_data,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to update solution article: {e}"}


@conditional_tool()
async def publish_solution_article(article_id: int) -> Dict[str, Any]:
    """Publish a draft KB article (sets status to 2=Published).

    This is a convenience wrapper — equivalent to updating status to 2."""
    client = get_client()
    try:
        response = await client.put(
            f"/api/v2/solutions/articles/{article_id}",
            json={"status": 2},
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to publish solution article: {e}"}
