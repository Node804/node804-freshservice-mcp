"""Local file search tools for discovering files to attach."""

import fnmatch
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..server import conditional_tool

logger = logging.getLogger(__name__)

_SEARCH_PATHS_RAW = os.getenv("FRESHSERVICE_FILE_SEARCH_PATHS", "")


def _get_search_roots() -> List[str]:
    """Parse and validate configured search root directories."""
    if not _SEARCH_PATHS_RAW.strip():
        return []
    roots = []
    for p in _SEARCH_PATHS_RAW.split(";"):
        p = p.strip()
        if p and os.path.isdir(p):
            roots.append(os.path.normpath(p))
    return roots


def _is_under_allowed_root(path: str, roots: List[str]) -> bool:
    """Check that a resolved path falls under one of the allowed roots."""
    real = os.path.realpath(path)
    return any(
        real.startswith(os.path.realpath(r) + os.sep) or real == os.path.realpath(r)
        for r in roots
    )


def _match_file(filename: str, query: str) -> bool:
    """Case-insensitive match: glob patterns or substring."""
    filename_lower = filename.lower()
    query_lower = query.lower()
    if any(c in query for c in ("*", "?", "[", "]")):
        return fnmatch.fnmatch(filename_lower, query_lower)
    return query_lower in filename_lower


@conditional_tool()
async def find_file(
    query: str,
    search_paths: Optional[List[str]] = None,
    recursive: bool = True,
    max_results: int = 25,
) -> Dict[str, Any]:
    """Search for files on the local filesystem by name pattern.

    Use this tool FIRST when the user asks to find, locate, or attach
    files from their system. When a user references files on "my machine",
    "my computer", or "my system", always use this tool before searching
    uploads or the web.

    Commonly used before add_ticket_attachment, add_note_attachment, or
    add_reply_attachment to locate files for upload.

    Searches are restricted to directories configured via the
    FRESHSERVICE_FILE_SEARCH_PATHS environment variable.

    Args:
        query: Filename to search for. Supports:
            - Partial name: "report" matches "Q4_report.pdf"
            - Glob pattern: "*.pdf" matches all PDFs
            - Exact name: "invoice_2024.xlsx"
            Matching is case-insensitive.
        search_paths: Optional list of specific directories to search
            (must be subdirectories of configured roots). If omitted,
            all configured roots are searched.
        recursive: Search subdirectories (default: True).
        max_results: Maximum files to return (default: 25, max: 100).
    """
    if not query or not query.strip():
        return {"error": "Search query is required."}

    query = query.strip()
    max_results = max(1, min(max_results, 100))

    allowed_roots = _get_search_roots()
    if not allowed_roots:
        return {
            "error": (
                "No search directories configured. Set the "
                "FRESHSERVICE_FILE_SEARCH_PATHS environment variable "
                "to a semicolon-separated list of directories."
            ),
        }

    if search_paths:
        validated: List[str] = []
        for sp in search_paths:
            sp = os.path.normpath(sp.strip())
            if not os.path.isdir(sp):
                return {"error": f"Search path is not a valid directory: {sp}"}
            if not _is_under_allowed_root(sp, allowed_roots):
                return {
                    "error": (
                        f"Search path '{sp}' is outside the allowed "
                        f"search directories."
                    ),
                }
            validated.append(sp)
        roots_to_search = validated
    else:
        roots_to_search = allowed_roots

    matches: List[Dict[str, Any]] = []
    seen: set = set()

    for root in roots_to_search:
        if recursive:
            for dirpath, _dirnames, filenames in os.walk(root):
                for fname in filenames:
                    if _match_file(fname, query):
                        full_path = os.path.join(dirpath, fname)
                        real_path = os.path.realpath(full_path)
                        if real_path in seen:
                            continue
                        seen.add(real_path)
                        try:
                            stat = os.stat(real_path)
                            matches.append({
                                "path": full_path,
                                "name": fname,
                                "size_bytes": stat.st_size,
                                "modified": datetime.fromtimestamp(
                                    stat.st_mtime, tz=timezone.utc
                                ).isoformat(),
                            })
                        except OSError:
                            continue
                        if len(matches) >= max_results:
                            break
                if len(matches) >= max_results:
                    break
        else:
            try:
                entries = os.listdir(root)
            except OSError:
                continue
            for fname in entries:
                full_path = os.path.join(root, fname)
                if not os.path.isfile(full_path):
                    continue
                if _match_file(fname, query):
                    real_path = os.path.realpath(full_path)
                    if real_path in seen:
                        continue
                    seen.add(real_path)
                    try:
                        stat = os.stat(real_path)
                        matches.append({
                            "path": full_path,
                            "name": fname,
                            "size_bytes": stat.st_size,
                            "modified": datetime.fromtimestamp(
                                stat.st_mtime, tz=timezone.utc
                            ).isoformat(),
                        })
                    except OSError:
                        continue
                    if len(matches) >= max_results:
                        break
        if len(matches) >= max_results:
            break

    truncated = len(matches) >= max_results

    return {
        "files": matches,
        "count": len(matches),
        "query": query,
        "search_roots": roots_to_search,
        "recursive": recursive,
        "truncated": truncated,
    }
