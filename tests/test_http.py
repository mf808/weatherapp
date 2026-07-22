import pytest
import requests

from conftest import FakeResponse
from src.utils import http
from src.utils.http import MAX_RESPONSE_BYTES, safe_get, safe_post


def _install(monkeypatch, verb, resp):
    """Patch requests.get/post inside the http module and capture kwargs."""
    captured = {}

    def fake(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return resp

    monkeypatch.setattr(http.requests, verb, fake)
    return captured


def test_safe_get_returns_response(monkeypatch):
    resp = FakeResponse({"ok": True})
    _install(monkeypatch, "get", resp)
    assert safe_get("http://x").json() == {"ok": True}


def test_safe_get_sets_default_timeout_and_stream(monkeypatch):
    captured = _install(monkeypatch, "get", FakeResponse())
    safe_get("http://x")
    assert captured["kwargs"]["timeout"] == (5, 10)
    assert captured["kwargs"]["stream"] is True


def test_caller_timeout_not_overridden(monkeypatch):
    captured = _install(monkeypatch, "get", FakeResponse())
    safe_get("http://x", timeout=(1, 2))
    assert captured["kwargs"]["timeout"] == (1, 2)


def test_safe_post_forwards_data(monkeypatch):
    captured = _install(monkeypatch, "post", FakeResponse({"token": "abc"}))
    safe_post("http://x", data={"grant_type": "refresh_token"})
    assert captured["kwargs"]["data"] == {"grant_type": "refresh_token"}


def test_http_error_propagates(monkeypatch):
    _install(monkeypatch, "get", FakeResponse(status_code=500))
    with pytest.raises(requests.HTTPError):
        safe_get("http://x")


# ── Edge cases: response-size guard ─────────────────────────────

def test_oversized_response_rejected(monkeypatch):
    resp = FakeResponse(headers={"content-length": str(MAX_RESPONSE_BYTES + 1)})
    _install(monkeypatch, "get", resp)
    with pytest.raises(ValueError, match="too large"):
        safe_get("http://x")
    assert resp.closed is True  # guard must release the connection


def test_response_at_exact_limit_allowed(monkeypatch):
    resp = FakeResponse(headers={"content-length": str(MAX_RESPONSE_BYTES)})
    _install(monkeypatch, "get", resp)
    safe_get("http://x")  # boundary is inclusive; must not raise


def test_missing_content_length_allowed(monkeypatch):
    _install(monkeypatch, "get", FakeResponse(headers={}))
    safe_get("http://x")  # no header → size unknown → not rejected
