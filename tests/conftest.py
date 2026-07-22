"""Shared fixtures.

All tests are static and repeatable: no network access, and anything that would
otherwise depend on the wall clock or the ambient timezone pins ``TZ`` explicitly.
"""

import os
from pathlib import Path

import pytest

from src.utils.fonts import FontRegistry

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _fixed_timezone(monkeypatch):
    """Pin TZ so every timestamp/date computation is deterministic across machines.

    The code reads ``os.environ["TZ"]`` (defaulting to Europe/Berlin) in several
    places; UTC keeps unix-timestamp assertions simple and DST-free.
    """
    monkeypatch.setenv("TZ", "UTC")


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def fonts() -> FontRegistry:
    return FontRegistry(str(REPO_ROOT / "fonts"))


@pytest.fixture
def icons_dir() -> str:
    return str(REPO_ROOT / "icons")


class FakeResponse:
    """Minimal stand-in for ``requests.Response`` used by the HTTP-mocking tests."""

    def __init__(self, json_data=None, *, status_code=200, headers=None, content=b""):
        self._json = json_data if json_data is not None else {}
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content
        self.closed = False

    def json(self):
        return self._json

    def iter_content(self, chunk_size=1):
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i:i + chunk_size]

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"status {self.status_code}")

    def close(self):
        self.closed = True
