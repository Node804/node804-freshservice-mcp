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


# ---------------------------------------------------------------------------
# Ticket Attachments
# ---------------------------------------------------------------------------


class TestAddTicketAttachment:
    def _make_mock_response(self, json_data, status_code=200):
        mock = MagicMock()
        mock.status_code = status_code
        mock.json.return_value = json_data
        mock.raise_for_status.return_value = None
        return mock

    @pytest.mark.asyncio
    async def test_file_not_found(self, mock_env):
        from freshservice_mcp.tools.tickets import add_ticket_attachment

        result = await add_ticket_attachment(
            ticket_id=1,
            file_path="/nonexistent/file.txt",
        )
        assert "error" in result
        assert "File not found" in result["error"]

    @pytest.mark.asyncio
    async def test_successful_upload(self, mock_env, tmp_path):
        from freshservice_mcp.tools.tickets import add_ticket_attachment

        # Create a temp file
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        fake_response = self._make_mock_response(
            {"ticket": {"id": 1, "attachments": [{"id": 10, "name": "test.txt"}]}}
        )

        with patch(
            "freshservice_mcp.tools.tickets.multipart_request",
            new_callable=AsyncMock,
            return_value=fake_response,
        ) as mock_req:
            result = await add_ticket_attachment(
                ticket_id=1,
                file_path=str(test_file),
            )

        assert "error" not in result
        assert result["success"] is True
        # Verify multipart_request was called with correct args
        call_args = mock_req.call_args
        assert call_args[0][0] == "PUT"
        assert "/api/v2/tickets/1" in call_args[0][1]


class TestAddNoteAttachment:
    def _make_mock_response(self, json_data, status_code=200):
        mock = MagicMock()
        mock.status_code = status_code
        mock.json.return_value = json_data
        mock.raise_for_status.return_value = None
        return mock

    @pytest.mark.asyncio
    async def test_empty_body(self, mock_env):
        from freshservice_mcp.tools.tickets import add_note_attachment

        result = await add_note_attachment(
            ticket_id=1,
            body="",
            file_path="/some/file.txt",
        )
        assert "error" in result
        assert "body" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_successful_note_with_attachment(self, mock_env, tmp_path):
        from freshservice_mcp.tools.tickets import add_note_attachment

        test_file = tmp_path / "report.pdf"
        test_file.write_bytes(b"%PDF-fake-content")

        fake_response = self._make_mock_response(
            {"conversation": {"id": 99, "body": "See attached"}}
        )

        with patch(
            "freshservice_mcp.tools.tickets.multipart_request",
            new_callable=AsyncMock,
            return_value=fake_response,
        ) as mock_req:
            result = await add_note_attachment(
                ticket_id=5,
                body="See attached",
                file_path=str(test_file),
            )

        assert "error" not in result
        call_args = mock_req.call_args
        assert call_args[0][0] == "POST"
        assert "/api/v2/tickets/5/notes" in call_args[0][1]
        assert call_args[1]["data"]["body"] == "See attached"


class TestAddReplyAttachment:
    def _make_mock_response(self, json_data, status_code=200):
        mock = MagicMock()
        mock.status_code = status_code
        mock.json.return_value = json_data
        mock.raise_for_status.return_value = None
        return mock

    @pytest.mark.asyncio
    async def test_empty_body(self, mock_env):
        from freshservice_mcp.tools.tickets import add_reply_attachment

        result = await add_reply_attachment(
            ticket_id=1,
            body="   ",
            file_path="/some/file.txt",
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_successful_reply_with_attachment(self, mock_env, tmp_path):
        from freshservice_mcp.tools.tickets import add_reply_attachment

        test_file = tmp_path / "screenshot.png"
        test_file.write_bytes(b"\x89PNG fake")

        fake_response = self._make_mock_response(
            {"conversation": {"id": 101, "body": "Please see screenshot"}}
        )

        with patch(
            "freshservice_mcp.tools.tickets.multipart_request",
            new_callable=AsyncMock,
            return_value=fake_response,
        ) as mock_req:
            result = await add_reply_attachment(
                ticket_id=7,
                body="Please see screenshot",
                file_path=str(test_file),
            )

        assert "error" not in result
        call_args = mock_req.call_args
        assert call_args[0][0] == "POST"
        assert "/api/v2/tickets/7/reply" in call_args[0][1]


class TestListTicketAttachments:
    @pytest.mark.asyncio
    async def test_list_attachments(self, mock_env):
        from freshservice_mcp.tools.tickets import list_ticket_attachments

        fake_attachments = [
            {"id": 10, "name": "doc.pdf", "size": 1024},
            {"id": 11, "name": "img.png", "size": 2048},
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ticket": {"id": 1, "attachments": fake_attachments}
        }
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch(
            "freshservice_mcp.tools.tickets.get_client",
            return_value=mock_client,
        ):
            result = await list_ticket_attachments(ticket_id=1)

        assert "error" not in result
        assert result["count"] == 2
        assert result["ticket_id"] == 1
        assert len(result["attachments"]) == 2


class TestDeleteTicketAttachment:
    @pytest.mark.asyncio
    async def test_successful_delete(self, mock_env):
        from freshservice_mcp.tools.tickets import delete_ticket_attachment

        mock_response = MagicMock()
        mock_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.delete.return_value = mock_response

        with patch(
            "freshservice_mcp.tools.tickets.get_client",
            return_value=mock_client,
        ):
            result = await delete_ticket_attachment(ticket_id=1, attachment_id=10)

        assert result["success"] is True
        mock_client.delete.assert_called_once_with(
            "/api/v2/tickets/1/attachments/10"
        )


class TestDeleteConversationAttachment:
    @pytest.mark.asyncio
    async def test_successful_delete(self, mock_env):
        from freshservice_mcp.tools.tickets import delete_conversation_attachment

        mock_response = MagicMock()
        mock_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.delete.return_value = mock_response

        with patch(
            "freshservice_mcp.tools.tickets.get_client",
            return_value=mock_client,
        ):
            result = await delete_conversation_attachment(
                conversation_id=99, attachment_id=20
            )

        assert result["success"] is True
        mock_client.delete.assert_called_once_with(
            "/api/v2/conversations/99/attachments/20"
        )
