"""Ticket and ticket conversation tools."""

import json
import logging
import urllib.parse
from typing import Any, Dict, List, Optional, Union

from ..server import conditional_tool
from ..client import get_client, parse_link_header, cached_response, FRESHSERVICE_DOMAIN
from ..models import TicketSource, TicketStatus, TicketPriority

logger = logging.getLogger(__name__)


@conditional_tool()
@cached_response()
async def get_ticket_fields() -> Dict[str, Any]:
    """Get the raw ticket form field definitions from Freshservice (cached).

    Returns field names, types, choices, and validation rules for every field
    on the ticket form.  Useful for discovering custom fields or building
    dynamic forms.

    Tip: For status lookups, prefer get_ticket_statuses which parses
    this data automatically and categorizes statuses as resolved/unresolved."""
    client = get_client()
    try:
        response = await client.get("/api/v2/ticket_form_fields")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch ticket fields: {e}"}


@conditional_tool()
@cached_response()
async def get_ticket_statuses() -> Dict[str, Any]:
    """Get all ticket statuses from Freshservice, categorized as resolved or unresolved.

    Fetches ticket form fields (cached), extracts the status field choices,
    and categorizes each status.  By Freshservice convention, status IDs 4
    (Resolved) and 5 (Closed) are "resolved"; all others — including custom
    statuses — are "unresolved".

    Returns:
        statuses: list of {id, name, category} for every status
        resolved_ids: list of status IDs considered resolved
        unresolved_ids: list of status IDs considered unresolved

    Costs 0 API calls when get_ticket_fields is already cached, 1 otherwise.
    """
    # get_ticket_fields is cached, so this is usually free
    fields_response = await get_ticket_fields()
    if "error" in fields_response:
        return fields_response

    # Locate the status field
    status_field = None
    ticket_fields = fields_response.get("ticket_fields", [])
    for field in ticket_fields:
        if field.get("name") == "status":
            status_field = field
            break

    if status_field is None:
        return {"error": "Status field not found in ticket form fields"}

    # Parse choices — handle the two common API response shapes
    choices = status_field.get("choices", {})
    statuses: List[Dict[str, Any]] = []

    if isinstance(choices, dict):
        # {"2": "Open", ...} or {"2": ["Open"], ...}
        for status_id_str, label in choices.items():
            try:
                status_id = int(status_id_str)
            except ValueError:
                continue
            if isinstance(label, list):
                label = label[0] if label else f"Status {status_id}"
            statuses.append({"id": status_id, "name": str(label)})
    elif isinstance(choices, list):
        # [["Open", 2], ...] or [{"id": 2, "value": "Open"}, ...]
        for choice in choices:
            if isinstance(choice, list) and len(choice) >= 2:
                statuses.append({"id": int(choice[1]), "name": str(choice[0])})
            elif isinstance(choice, dict):
                sid = choice.get("id") or choice.get("value")
                sname = choice.get("value") or choice.get("name", "")
                if sid is not None:
                    statuses.append({"id": int(sid), "name": str(sname)})

    # Categorize: 4 (Resolved) and 5 (Closed) are resolved by Freshservice convention
    RESOLVED_IDS = {4, 5}
    resolved_ids: List[int] = []
    unresolved_ids: List[int] = []

    for status in statuses:
        category = "resolved" if status["id"] in RESOLVED_IDS else "unresolved"
        status["category"] = category
        if category == "resolved":
            resolved_ids.append(status["id"])
        else:
            unresolved_ids.append(status["id"])

    return {
        "statuses": statuses,
        "resolved_ids": sorted(resolved_ids),
        "unresolved_ids": sorted(unresolved_ids),
    }


@conditional_tool()
async def get_my_tickets(
    status_filter: str = "unresolved",
    page: int = 1,
) -> Dict[str, Any]:
    """Get tickets assigned to the current authenticated agent.

    Combines get_current_agent (cached) + get_ticket_statuses (cached) +
    a single filter API call.  On a warm cache this costs exactly 1 API call.

    Args:
        status_filter: Which tickets to return.
            "unresolved" (default) — all tickets that are NOT Resolved or Closed.
            "resolved" — only Resolved and Closed tickets.
            "all" — every ticket regardless of status.
        page: Page number for results (default: 1).

    Returns the matching tickets, the filter query that was used, and status metadata.
    """
    valid_filters = {"unresolved", "resolved", "all"}
    if status_filter not in valid_filters:
        return {
            "error": f"Invalid status_filter '{status_filter}'. "
            f"Must be one of: {', '.join(sorted(valid_filters))}"
        }

    # Step 1: Get current agent (cached 1 hr) — lazy import to avoid circular deps
    from .agents import get_current_agent

    agent_response = await get_current_agent()
    if "error" in agent_response:
        return {"error": f"Could not determine current agent: {agent_response['error']}"}

    agent = agent_response.get("agent", {})
    agent_id = agent.get("id")
    if not agent_id:
        return {"error": "Could not determine agent ID from current agent response"}

    # Step 2: Build status clause
    if status_filter == "all":
        query = f"agent_id:{agent_id}"
    else:
        statuses_response = await get_ticket_statuses()
        if "error" in statuses_response:
            return {
                "error": f"Could not determine ticket statuses: {statuses_response['error']}"
            }

        target_ids = (
            statuses_response["unresolved_ids"]
            if status_filter == "unresolved"
            else statuses_response["resolved_ids"]
        )

        if not target_ids:
            return {
                "tickets": [],
                "total": 0,
                "query_used": f"agent_id:{agent_id} (no matching statuses)",
                "status_filter": status_filter,
            }

        status_clause = " OR ".join(f"status:{sid}" for sid in target_ids)
        query = f"agent_id:{agent_id} AND ({status_clause})"

    # Step 3: Call filter API
    encoded_query = urllib.parse.quote(f'"{query}"')
    url = f"/api/v2/tickets/filter?query={encoded_query}&page={page}"

    client = get_client()
    try:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        return {
            "tickets": data.get("tickets", []),
            "total": data.get("total", len(data.get("tickets", []))),
            "query_used": query,
            "status_filter": status_filter,
            "agent_id": agent_id,
            "page": page,
        }
    except Exception as e:
        return {"error": f"Failed to fetch tickets: {e}"}


@conditional_tool()
async def get_tickets(
    page: Optional[int] = 1,
    per_page: Optional[int] = 30,
) -> Dict[str, Any]:
    """List tickets from Freshservice ordered by created_at descending.

    Returns all tickets across the tenant (not filtered).  For targeted
    queries, prefer filter_tickets (custom query) or get_my_tickets
    (current agent's tickets).

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
            "/api/v2/tickets",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()

        pagination_info = parse_link_header(response.headers.get("Link", ""))
        return {
            "tickets": response.json(),
            "pagination": {
                "current_page": page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "per_page": per_page,
            },
        }
    except Exception as e:
        return {"error": f"Failed to fetch tickets: {e}"}


@conditional_tool()
async def get_ticket_by_id(ticket_id: int) -> Dict[str, Any]:
    """Fetch a single ticket by its numeric ID.

    Returns full ticket details including subject, description, status,
    priority, requester, agent, custom fields, and timestamps."""
    client = get_client()
    try:
        response = await client.get(f"/api/v2/tickets/{ticket_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch ticket: {e}"}


@conditional_tool()
async def create_ticket(
    subject: str,
    description: str,
    source: Union[int, str],
    priority: Union[int, str],
    status: Union[int, str],
    email: Optional[str] = None,
    requester_id: Optional[int] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a new ticket in Freshservice.

    Requires either email or requester_id to identify the requester.

    Args:
        subject: Ticket subject line
        description: Ticket body (HTML supported)
        source: Origin channel — 1=Email, 2=Portal, 3=Phone, 7=Yammer,
                9=Feedback Widget, 10=Outbound Email
        priority: 1=Low, 2=Medium, 3=High, 4=Urgent
        status: 2=Open, 3=Pending, 4=Resolved, 5=Closed
        email: Requester email (creates requester if new)
        requester_id: Existing requester ID (alternative to email)
        custom_fields: Dict of custom field name→value pairs"""
    if not email and not requester_id:
        return {"error": "Either email or requester_id must be provided"}

    try:
        source_val = int(source)
        priority_val = int(priority)
        status_val = int(status)
    except ValueError:
        return {"error": "Invalid value for source, priority, or status"}

    if (
        source_val not in [e.value for e in TicketSource]
        or priority_val not in [e.value for e in TicketPriority]
        or status_val not in [e.value for e in TicketStatus]
    ):
        return {"error": "Invalid value for source, priority, or status"}

    data: Dict[str, Any] = {
        "subject": subject,
        "description": description,
        "source": source_val,
        "priority": priority_val,
        "status": status_val,
    }
    if email:
        data["email"] = email
    if requester_id:
        data["requester_id"] = requester_id
    if custom_fields:
        data["custom_fields"] = custom_fields

    client = get_client()
    try:
        response = await client.post("/api/v2/tickets", json=data)
        response.raise_for_status()
        return {"success": True, "ticket": response.json()}
    except Exception as e:
        return {"error": f"Failed to create ticket: {e}"}


@conditional_tool()
async def update_ticket(
    ticket_id: int,
    ticket_fields: Dict[str, Any],
) -> Dict[str, Any]:
    """Update fields on an existing ticket.

    Args:
        ticket_id: The ticket to update
        ticket_fields: Dict of field name→value pairs.  Common fields:
            status, priority, agent_id, group_id, subject, description.
            Nest custom fields under a "custom_fields" key."""
    if not ticket_fields:
        return {"error": "No fields provided for update"}

    custom_fields = ticket_fields.pop("custom_fields", {})
    update_data = dict(ticket_fields)
    if custom_fields:
        update_data["custom_fields"] = custom_fields

    client = get_client()
    try:
        response = await client.put(f"/api/v2/tickets/{ticket_id}", json=update_data)
        response.raise_for_status()
        return {
            "success": True,
            "message": "Ticket updated successfully",
            "ticket": response.json(),
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to update ticket: {e}"}


@conditional_tool()
async def filter_tickets(
    query: str,
    page: int = 1,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Search tickets using Freshservice's filter query syntax.

    Query examples:
        "status:2"                          — all Open tickets
        "priority:4 AND status:2"           — Urgent + Open
        "agent_id:12345"                    — assigned to agent 12345
        "group_id:67 AND (status:2 OR status:3)" — group's Open/Pending
        "created_at:>'2024-01-01'"          — created after a date
        "tag:'VPN'"                         — tickets tagged VPN

    Supported operators: AND, OR, >, <, :  (colon = equals).
    String values with spaces must be wrapped in single quotes inside
    the query.  For the current agent's tickets, prefer get_my_tickets.

    Args:
        query: Filter query string
        page: Page number (default: 1)
        workspace_id: Optional workspace ID filter"""
    encoded_query = urllib.parse.quote(f'"{query}"')
    url = f"/api/v2/tickets/filter?query={encoded_query}&page={page}"
    if workspace_id is not None:
        url += f"&workspace_id={workspace_id}"

    client = get_client()
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to filter tickets: {e}"}


@conditional_tool()
async def delete_ticket(ticket_id: int) -> Dict[str, Any]:
    """Permanently delete a ticket.  This cannot be undone."""
    client = get_client()
    try:
        response = await client.delete(f"/api/v2/tickets/{ticket_id}")
        if response.status_code == 204:
            return {"success": True, "message": "Ticket deleted successfully"}
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to delete ticket: {e}"}


# --- Ticket Conversations ---


@conditional_tool()
async def send_ticket_reply(
    ticket_id: int,
    body: str,
    from_email: Optional[str] = None,
    user_id: Optional[int] = None,
    cc_emails: Optional[Union[str, List[str]]] = None,
    bcc_emails: Optional[Union[str, List[str]]] = None,
) -> Dict[str, Any]:
    """Send an email reply to the ticket requester.

    This creates an outbound email visible to the requester.  For internal-only
    comments (not emailed), use create_ticket_note instead.

    Args:
        ticket_id: The ticket to reply to
        body: Reply content (HTML supported)
        from_email: Sender address (defaults to helpdesk@<domain>)
        user_id: Agent ID sending the reply
        cc_emails: CC recipients (list of emails or JSON string)
        bcc_emails: BCC recipients (list of emails or JSON string)"""
    if not ticket_id or not isinstance(ticket_id, int) or ticket_id < 1:
        return {"error": "Invalid ticket_id: Must be an integer >= 1"}
    if not body or not isinstance(body, str) or not body.strip():
        return {"error": "Missing or empty body: Reply content is required"}

    def parse_emails(value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return []
        return value or []

    payload: Dict[str, Any] = {
        "body": body.strip(),
        "from_email": from_email or f"helpdesk@{FRESHSERVICE_DOMAIN}",
    }
    if user_id is not None:
        payload["user_id"] = user_id
    parsed_cc = parse_emails(cc_emails)
    if parsed_cc:
        payload["cc_emails"] = parsed_cc
    parsed_bcc = parse_emails(bcc_emails)
    if parsed_bcc:
        payload["bcc_emails"] = parsed_bcc

    client = get_client()
    try:
        response = await client.post(f"/api/v2/tickets/{ticket_id}/reply", json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to send ticket reply: {e}"}


@conditional_tool()
async def create_ticket_note(
    ticket_id: int,
    body: str,
) -> Dict[str, Any]:
    """Add an internal note to a ticket (not emailed to the requester).

    Use this for agent-to-agent communication or internal record-keeping.
    To send a reply that the requester can see, use send_ticket_reply."""
    client = get_client()
    try:
        response = await client.post(
            f"/api/v2/tickets/{ticket_id}/notes",
            json={"body": body},
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to create ticket note: {e}"}


@conditional_tool()
async def update_ticket_conversation(
    conversation_id: int,
    body: str,
) -> Dict[str, Any]:
    """Edit the body of an existing ticket reply or note.

    Requires the conversation_id (not the ticket_id).  Use
    list_all_ticket_conversation to find conversation IDs."""
    client = get_client()
    try:
        response = await client.put(
            f"/api/v2/conversations/{conversation_id}",
            json={"body": body},
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to update conversation: {e}"}


@conditional_tool()
async def list_all_ticket_conversation(
    ticket_id: int,
    page: int = 1,
    per_page: int = 30,
) -> Dict[str, Any]:
    """List all replies and notes on a ticket in chronological order.

    Conversations include both outbound replies (visible to requester)
    and internal notes (agent-only).  Each entry has an 'incoming' flag
    and a 'private' flag to distinguish them.

    Args:
        ticket_id: The ID of the ticket
        page: Page number (default: 1)
        per_page: Items per page (1-100, default: 30)"""
    if page < 1:
        return {"error": "Page number must be greater than 0"}
    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    client = get_client()
    try:
        response = await client.get(
            f"/api/v2/tickets/{ticket_id}/conversations",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()

        pagination_info = parse_link_header(response.headers.get("Link", ""))
        return {
            "conversations": response.json(),
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "next_page": pagination_info.get("next"),
                "prev_page": pagination_info.get("prev"),
                "has_more": pagination_info.get("next") is not None,
            },
        }
    except Exception as e:
        return {"error": f"Failed to fetch ticket conversations: {e}"}
