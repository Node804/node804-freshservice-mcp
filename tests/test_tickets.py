"""Tests for get_ticket_statuses and get_my_tickets convenience tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ticket_fields_response(choices):
    """Build a fake get_ticket_fields response with the given status choices."""
    return {
        "ticket_fields": [
            {"name": "requester", "label": "Requester"},
            {
                "name": "status",
                "label": "Status",
                "choices": choices,
            },
            {"name": "priority", "label": "Priority"},
        ],
    }


STANDARD_CHOICES_DICT = {
    "2": "Open",
    "3": "Pending",
    "4": "Resolved",
    "5": "Closed",
}

CUSTOM_CHOICES_DICT = {
    "2": "Open",
    "3": "Pending",
    "4": "Resolved",
    "5": "Closed",
    "6": "Awaiting Vendor",
    "7": "On Hold",
}

LIST_CHOICES = [
    ["Open", 2],
    ["Pending", 3],
    ["Resolved", 4],
    ["Closed", 5],
]


# ---------------------------------------------------------------------------
# get_ticket_statuses
# ---------------------------------------------------------------------------


class TestGetTicketStatuses:
    @pytest.mark.asyncio
    async def test_standard_statuses_dict(self, mock_env):
        from freshservice_mcp.client import _response_cache

        _response_cache.clear()

        from freshservice_mcp.tools.tickets import get_ticket_statuses

        fake_fields = _make_ticket_fields_response(STANDARD_CHOICES_DICT)

        with patch(
            "freshservice_mcp.tools.tickets.get_ticket_fields",
            new_callable=AsyncMock,
            return_value=fake_fields,
        ):
            result = await get_ticket_statuses()

        assert "error" not in result
        assert sorted(result["resolved_ids"]) == [4, 5]
        assert sorted(result["unresolved_ids"]) == [2, 3]
        assert len(result["statuses"]) == 4

    @pytest.mark.asyncio
    async def test_custom_statuses_classified_unresolved(self, mock_env):
        from freshservice_mcp.client import _response_cache

        _response_cache.clear()

        from freshservice_mcp.tools.tickets import get_ticket_statuses

        fake_fields = _make_ticket_fields_response(CUSTOM_CHOICES_DICT)

        with patch(
            "freshservice_mcp.tools.tickets.get_ticket_fields",
            new_callable=AsyncMock,
            return_value=fake_fields,
        ):
            result = await get_ticket_statuses()

        assert "error" not in result
        # Custom statuses 6 and 7 should be unresolved
        assert sorted(result["unresolved_ids"]) == [2, 3, 6, 7]
        assert sorted(result["resolved_ids"]) == [4, 5]
        assert len(result["statuses"]) == 6

    @pytest.mark.asyncio
    async def test_list_format_choices(self, mock_env):
        from freshservice_mcp.client import _response_cache

        _response_cache.clear()

        from freshservice_mcp.tools.tickets import get_ticket_statuses

        fake_fields = _make_ticket_fields_response(LIST_CHOICES)

        with patch(
            "freshservice_mcp.tools.tickets.get_ticket_fields",
            new_callable=AsyncMock,
            return_value=fake_fields,
        ):
            result = await get_ticket_statuses()

        assert "error" not in result
        assert sorted(result["resolved_ids"]) == [4, 5]
        assert sorted(result["unresolved_ids"]) == [2, 3]

    @pytest.mark.asyncio
    async def test_propagates_error_from_get_ticket_fields(self, mock_env):
        from freshservice_mcp.client import _response_cache

        _response_cache.clear()

        from freshservice_mcp.tools.tickets import get_ticket_statuses

        with patch(
            "freshservice_mcp.tools.tickets.get_ticket_fields",
            new_callable=AsyncMock,
            return_value={"error": "Failed to fetch ticket fields: timeout"},
        ):
            result = await get_ticket_statuses()

        assert "error" in result
        assert "timeout" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_status_field(self, mock_env):
        from freshservice_mcp.client import _response_cache

        _response_cache.clear()

        from freshservice_mcp.tools.tickets import get_ticket_statuses

        fake_fields = {
            "ticket_fields": [
                {"name": "requester", "label": "Requester"},
                {"name": "priority", "label": "Priority"},
            ]
        }

        with patch(
            "freshservice_mcp.tools.tickets.get_ticket_fields",
            new_callable=AsyncMock,
            return_value=fake_fields,
        ):
            result = await get_ticket_statuses()

        assert "error" in result
        assert "Status field not found" in result["error"]

    @pytest.mark.asyncio
    async def test_each_status_has_category(self, mock_env):
        from freshservice_mcp.client import _response_cache

        _response_cache.clear()

        from freshservice_mcp.tools.tickets import get_ticket_statuses

        fake_fields = _make_ticket_fields_response(STANDARD_CHOICES_DICT)

        with patch(
            "freshservice_mcp.tools.tickets.get_ticket_fields",
            new_callable=AsyncMock,
            return_value=fake_fields,
        ):
            result = await get_ticket_statuses()

        for status in result["statuses"]:
            assert "category" in status
            assert status["category"] in ("resolved", "unresolved")
            assert "id" in status
            assert "name" in status


# ---------------------------------------------------------------------------
# get_my_tickets
# ---------------------------------------------------------------------------

FAKE_AGENT = {"agent": {"id": 12345, "first_name": "Test", "email": "test@example.com"}}

FAKE_STATUSES = {
    "statuses": [
        {"id": 2, "name": "Open", "category": "unresolved"},
        {"id": 3, "name": "Pending", "category": "unresolved"},
        {"id": 4, "name": "Resolved", "category": "resolved"},
        {"id": 5, "name": "Closed", "category": "resolved"},
    ],
    "resolved_ids": [4, 5],
    "unresolved_ids": [2, 3],
}

FAKE_FILTER_RESPONSE = {
    "tickets": [
        {"id": 100, "subject": "Test ticket", "status": 2},
        {"id": 101, "subject": "Another ticket", "status": 3},
    ],
    "total": 2,
}


class TestGetMyTickets:
    def _make_mock_response(self, json_data, status_code=200):
        """Create a mock httpx response (sync methods like .json(), .raise_for_status())."""
        mock = MagicMock()
        mock.status_code = status_code
        mock.json.return_value = json_data
        mock.raise_for_status.return_value = None
        return mock

    @pytest.mark.asyncio
    async def test_unresolved_default(self, mock_env):
        from freshservice_mcp.client import _response_cache

        _response_cache.clear()

        from freshservice_mcp.tools.tickets import get_my_tickets

        mock_client = AsyncMock()
        mock_client.get.return_value = self._make_mock_response(FAKE_FILTER_RESPONSE)

        with (
            patch(
                "freshservice_mcp.tools.tickets.get_client",
                return_value=mock_client,
            ),
            patch(
                "freshservice_mcp.tools.agents.get_current_agent",
                new_callable=AsyncMock,
                return_value=FAKE_AGENT,
            ),
            patch(
                "freshservice_mcp.tools.tickets.get_ticket_statuses",
                new_callable=AsyncMock,
                return_value=FAKE_STATUSES,
            ),
        ):
            result = await get_my_tickets()

        assert "error" not in result
        assert result["status_filter"] == "unresolved"
        assert result["agent_id"] == 12345
        assert "agent_id:12345" in result["query_used"]
        assert "status:2" in result["query_used"]
        assert "status:3" in result["query_used"]
        assert len(result["tickets"]) == 2

    @pytest.mark.asyncio
    async def test_resolved_filter(self, mock_env):
        from freshservice_mcp.client import _response_cache

        _response_cache.clear()

        from freshservice_mcp.tools.tickets import get_my_tickets

        mock_client = AsyncMock()
        mock_client.get.return_value = self._make_mock_response(
            {"tickets": [], "total": 0}
        )

        with (
            patch(
                "freshservice_mcp.tools.tickets.get_client",
                return_value=mock_client,
            ),
            patch(
                "freshservice_mcp.tools.agents.get_current_agent",
                new_callable=AsyncMock,
                return_value=FAKE_AGENT,
            ),
            patch(
                "freshservice_mcp.tools.tickets.get_ticket_statuses",
                new_callable=AsyncMock,
                return_value=FAKE_STATUSES,
            ),
        ):
            result = await get_my_tickets(status_filter="resolved")

        assert "error" not in result
        assert result["status_filter"] == "resolved"
        assert "status:4" in result["query_used"]
        assert "status:5" in result["query_used"]

    @pytest.mark.asyncio
    async def test_all_filter_skips_status_lookup(self, mock_env):
        from freshservice_mcp.client import _response_cache

        _response_cache.clear()

        from freshservice_mcp.tools.tickets import get_my_tickets

        mock_client = AsyncMock()
        mock_client.get.return_value = self._make_mock_response(FAKE_FILTER_RESPONSE)

        statuses_mock = AsyncMock(return_value=FAKE_STATUSES)

        with (
            patch(
                "freshservice_mcp.tools.tickets.get_client",
                return_value=mock_client,
            ),
            patch(
                "freshservice_mcp.tools.agents.get_current_agent",
                new_callable=AsyncMock,
                return_value=FAKE_AGENT,
            ),
            patch(
                "freshservice_mcp.tools.tickets.get_ticket_statuses",
                statuses_mock,
            ),
        ):
            result = await get_my_tickets(status_filter="all")

        assert "error" not in result
        assert result["query_used"] == "agent_id:12345"
        # get_ticket_statuses should NOT have been called
        statuses_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_status_filter(self, mock_env):
        from freshservice_mcp.client import _response_cache

        _response_cache.clear()

        from freshservice_mcp.tools.tickets import get_my_tickets

        result = await get_my_tickets(status_filter="invalid")
        assert "error" in result
        assert "Invalid status_filter" in result["error"]

    @pytest.mark.asyncio
    async def test_agent_error_propagates(self, mock_env):
        from freshservice_mcp.client import _response_cache

        _response_cache.clear()

        from freshservice_mcp.tools.tickets import get_my_tickets

        with patch(
            "freshservice_mcp.tools.agents.get_current_agent",
            new_callable=AsyncMock,
            return_value={"error": "Failed to fetch current agent: timeout"},
        ):
            result = await get_my_tickets()

        assert "error" in result
        assert "Could not determine current agent" in result["error"]

    @pytest.mark.asyncio
    async def test_pagination_passed_through(self, mock_env):
        from freshservice_mcp.client import _response_cache

        _response_cache.clear()

        from freshservice_mcp.tools.tickets import get_my_tickets

        mock_client = AsyncMock()
        mock_client.get.return_value = self._make_mock_response(FAKE_FILTER_RESPONSE)

        with (
            patch(
                "freshservice_mcp.tools.tickets.get_client",
                return_value=mock_client,
            ),
            patch(
                "freshservice_mcp.tools.agents.get_current_agent",
                new_callable=AsyncMock,
                return_value=FAKE_AGENT,
            ),
            patch(
                "freshservice_mcp.tools.tickets.get_ticket_statuses",
                new_callable=AsyncMock,
                return_value=FAKE_STATUSES,
            ),
        ):
            result = await get_my_tickets(page=3)

        assert result["page"] == 3
        # Verify the URL passed to client includes page=3
        call_args = mock_client.get.call_args
        assert "page=3" in call_args[0][0]
