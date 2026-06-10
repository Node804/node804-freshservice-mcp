"""Tests for the find_file local file search tool."""

import os
import pytest


class TestFindFile:

    @pytest.mark.asyncio
    async def test_empty_query_returns_error(self, monkeypatch):
        monkeypatch.setattr("freshservice_mcp.tools.files._SEARCH_PATHS_RAW", "C:\\fake")
        from freshservice_mcp.tools.files import find_file
        result = await find_file(query="")
        assert "error" in result
        assert "required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_no_search_paths_configured(self, monkeypatch):
        monkeypatch.setattr("freshservice_mcp.tools.files._SEARCH_PATHS_RAW", "")
        from freshservice_mcp.tools.files import find_file
        result = await find_file(query="test.txt")
        assert "error" in result
        assert "FRESHSERVICE_FILE_SEARCH_PATHS" in result["error"]

    @pytest.mark.asyncio
    async def test_finds_matching_files(self, tmp_path, monkeypatch):
        (tmp_path / "report_q4.pdf").write_text("fake pdf")
        (tmp_path / "report_q3.pdf").write_text("fake pdf")
        (tmp_path / "notes.txt").write_text("notes")

        monkeypatch.setattr(
            "freshservice_mcp.tools.files._SEARCH_PATHS_RAW",
            str(tmp_path),
        )
        from freshservice_mcp.tools.files import find_file
        result = await find_file(query="report")

        assert "error" not in result
        assert result["count"] == 2
        names = {f["name"] for f in result["files"]}
        assert names == {"report_q4.pdf", "report_q3.pdf"}

    @pytest.mark.asyncio
    async def test_case_insensitive(self, tmp_path, monkeypatch):
        (tmp_path / "MyReport.PDF").write_text("data")

        monkeypatch.setattr(
            "freshservice_mcp.tools.files._SEARCH_PATHS_RAW",
            str(tmp_path),
        )
        from freshservice_mcp.tools.files import find_file
        result = await find_file(query="myreport")

        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_glob_pattern(self, tmp_path, monkeypatch):
        (tmp_path / "data.csv").write_text("a,b")
        (tmp_path / "data.xlsx").write_text("fake")
        (tmp_path / "readme.md").write_text("hi")

        monkeypatch.setattr(
            "freshservice_mcp.tools.files._SEARCH_PATHS_RAW",
            str(tmp_path),
        )
        from freshservice_mcp.tools.files import find_file
        result = await find_file(query="*.csv")

        assert result["count"] == 1
        assert result["files"][0]["name"] == "data.csv"

    @pytest.mark.asyncio
    async def test_recursive_search(self, tmp_path, monkeypatch):
        subdir = tmp_path / "sub" / "deep"
        subdir.mkdir(parents=True)
        (subdir / "nested.txt").write_text("deep file")

        monkeypatch.setattr(
            "freshservice_mcp.tools.files._SEARCH_PATHS_RAW",
            str(tmp_path),
        )
        from freshservice_mcp.tools.files import find_file
        result = await find_file(query="nested", recursive=True)

        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_non_recursive_skips_subdirs(self, tmp_path, monkeypatch):
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("deep file")
        (tmp_path / "top.txt").write_text("top")

        monkeypatch.setattr(
            "freshservice_mcp.tools.files._SEARCH_PATHS_RAW",
            str(tmp_path),
        )
        from freshservice_mcp.tools.files import find_file
        result = await find_file(query="nested", recursive=False)

        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_max_results_caps_output(self, tmp_path, monkeypatch):
        for i in range(10):
            (tmp_path / f"file_{i}.txt").write_text(f"content {i}")

        monkeypatch.setattr(
            "freshservice_mcp.tools.files._SEARCH_PATHS_RAW",
            str(tmp_path),
        )
        from freshservice_mcp.tools.files import find_file
        result = await find_file(query="file_", max_results=3)

        assert result["count"] == 3
        assert result["truncated"] is True

    @pytest.mark.asyncio
    async def test_search_path_outside_roots_rejected(self, tmp_path, monkeypatch):
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        forbidden = tmp_path / "forbidden"
        forbidden.mkdir()

        monkeypatch.setattr(
            "freshservice_mcp.tools.files._SEARCH_PATHS_RAW",
            str(allowed),
        )
        from freshservice_mcp.tools.files import find_file
        result = await find_file(query="*", search_paths=[str(forbidden)])

        assert "error" in result
        assert "outside" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_metadata_fields_present(self, tmp_path, monkeypatch):
        (tmp_path / "doc.txt").write_text("hello")

        monkeypatch.setattr(
            "freshservice_mcp.tools.files._SEARCH_PATHS_RAW",
            str(tmp_path),
        )
        from freshservice_mcp.tools.files import find_file
        result = await find_file(query="doc")

        f = result["files"][0]
        assert "path" in f
        assert "name" in f
        assert "size_bytes" in f
        assert "modified" in f
        assert f["size_bytes"] == 5  # len("hello")

    @pytest.mark.asyncio
    async def test_no_matches_returns_empty(self, tmp_path, monkeypatch):
        (tmp_path / "readme.md").write_text("hi")

        monkeypatch.setattr(
            "freshservice_mcp.tools.files._SEARCH_PATHS_RAW",
            str(tmp_path),
        )
        from freshservice_mcp.tools.files import find_file
        result = await find_file(query="nonexistent")

        assert result["count"] == 0
        assert result["files"] == []
        assert result["truncated"] is False
