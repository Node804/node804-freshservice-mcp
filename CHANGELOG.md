# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/).

## [1.4.0] - 2026-10-17

### Fixed
- Package failed at startup on fresh installs because `mcp` 2.x (which removed
  `mcp.server.fastmcp`) was being resolved. The dependency is now constrained
  to `mcp[cli]>=1.3.0,<2`.

### Added
- `get_ticket_by_id` automatically fetches catalog items for "Service Request"
  tickets and returns them as `ticket.requested_items`. A new
  `include_requested_items` parameter forces (`True`) or skips (`False`) the
  extra lookup. If the items call fails, the ticket is still returned with a
  `requested_items_error` field.
- `get_my_tickets`, `get_tickets`, and `filter_tickets` now return
  `service_request_ids` and a `service_request_note` when a page contains
  service requests, since list endpoints don't include catalog items.

### Changed
- `get_requested_items` shares its fetch logic with `get_ticket_by_id` via a new
  internal `fetch_requested_items` helper.
- Version strings in `pyproject.toml`, `__init__.py`, and README install
  examples are back in sync.

## [1.3.1] - 2026-07-17

### Changed
- Project metadata updates.

## [1.3.0] - 2026-07-17

### Added
- `list_ticket_approvals` and `view_ticket_approval` read-only tools.

## [1.2.0] - 2026-06-10

### Changed
- README build badges.

## [1.1.0] - 2026-06-10

### Added
- Ticket, note, and reply attachment tools.
- Agent signature appended to ticket replies.

[1.4.0]: https://github.com/Node804/node804-freshservice-mcp/compare/v1.3.1...v1.4.0
[1.3.1]: https://github.com/Node804/node804-freshservice-mcp/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/Node804/node804-freshservice-mcp/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Node804/node804-freshservice-mcp/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/Node804/node804-freshservice-mcp/releases/tag/v1.1.0
