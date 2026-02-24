"""Shared test fixtures."""

import os
import pytest


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Provide fake credentials so modules can be imported without real env vars."""
    monkeypatch.setenv("FRESHSERVICE_DOMAIN", "test.freshservice.com")
    monkeypatch.setenv("FRESHSERVICE_APIKEY", "test_api_key")
    monkeypatch.setenv("FRESHSERVICE_MODE", "admin")
