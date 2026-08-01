import sys

import pytest
import requests

import entrypoint

AZURE_ENV_VARS = ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET")
FETCHED_ENV_VARS = ("CLIENT_ID", "CLIENT_SECRET", "DEVICE_ID", "OUTDOOMODULE_ID", "OPENWEATHERMAP_APPID")


class FakeTokenResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"access_token": "fake-token"}


class FakeSecretResponse:
    def __init__(self, value):
        self._value = value

    def raise_for_status(self):
        pass

    def json(self):
        return {"value": self._value}


def _patch_exec(monkeypatch):
    execed = {}
    monkeypatch.setattr(entrypoint.os, "execvp", lambda file, args: execed.update(file=file, args=args))
    monkeypatch.setattr(sys, "argv", ["entrypoint.py", "python", "-m", "src.server"])
    return execed


def test_retry_recovers_from_transient_failure(monkeypatch):
    sleeps = []
    monkeypatch.setattr(entrypoint.time, "sleep", lambda s: sleeps.append(s))

    calls = {"n": 0}

    def flaky(x):
        calls["n"] += 1
        if calls["n"] < 3:
            raise requests.ConnectionError("transient")
        return "ok"

    result = entrypoint._retry(flaky, "arg")

    assert result == "ok"
    assert calls["n"] == 3
    assert sleeps == [1, 2]  # exponential backoff, one sleep per failed attempt


def test_retry_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr(entrypoint.time, "sleep", lambda s: None)

    def always_fails():
        raise requests.ConnectionError("persistent")

    with pytest.raises(requests.ConnectionError):
        entrypoint._retry(always_fails)


def test_no_bootstrap_credential_skips_vault_and_execs_directly(monkeypatch):
    for var in AZURE_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    def fail_if_called(*a, **k):
        raise AssertionError("should not touch the network with no bootstrap credential set")

    monkeypatch.setattr(entrypoint.requests, "post", fail_if_called)
    monkeypatch.setattr(entrypoint.requests, "get", fail_if_called)
    execed = _patch_exec(monkeypatch)

    entrypoint.main()

    assert execed == {"file": "python", "args": ["python", "-m", "src.server"]}


def test_fetches_secrets_and_seeds_missing_creds_json(monkeypatch, tmp_path):
    monkeypatch.setenv("AZURE_TENANT_ID", "tenant")
    monkeypatch.setenv("AZURE_CLIENT_ID", "client")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret")
    for var in FETCHED_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    creds_path = tmp_path / "creds.json"
    monkeypatch.setattr(entrypoint, "CREDS_JSON_PATH", str(creds_path))
    monkeypatch.setattr(entrypoint.requests, "post", lambda *a, **k: FakeTokenResponse())

    def fake_get(url, params=None, headers=None, timeout=None):
        name = url.rsplit("/", 1)[-1]
        return FakeSecretResponse(f"value-for-{name}")

    monkeypatch.setattr(entrypoint.requests, "get", fake_get)
    execed = _patch_exec(monkeypatch)

    entrypoint.main()

    assert entrypoint.os.environ["CLIENT_ID"] == "value-for-nas-weatherapp-netatmo-client-id"
    assert entrypoint.os.environ["OPENWEATHERMAP_APPID"] == "value-for-nas-weatherapp-owm-appid"
    assert creds_path.read_text() == "value-for-nas-weatherapp-creds-json"
    assert execed == {"file": "python", "args": ["python", "-m", "src.server"]}


def test_does_not_overwrite_existing_creds_json(monkeypatch, tmp_path):
    """A rotated, already-valid refresh_token must never be clobbered by the
    vault's point-in-time snapshot on a routine restart."""
    monkeypatch.setenv("AZURE_TENANT_ID", "tenant")
    monkeypatch.setenv("AZURE_CLIENT_ID", "client")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret")
    for var in FETCHED_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    creds_path = tmp_path / "creds.json"
    creds_path.write_text('{"refresh_token": "still-valid"}')
    monkeypatch.setattr(entrypoint, "CREDS_JSON_PATH", str(creds_path))
    monkeypatch.setattr(entrypoint.requests, "post", lambda *a, **k: FakeTokenResponse())

    def fail_if_creds_fetched(url, params=None, headers=None, timeout=None):
        name = url.rsplit("/", 1)[-1]
        if name == entrypoint.CREDS_JSON_SECRET:
            raise AssertionError("must not fetch creds.json from the vault when a local copy already exists")
        return FakeSecretResponse(f"value-for-{name}")

    monkeypatch.setattr(entrypoint.requests, "get", fail_if_creds_fetched)
    _patch_exec(monkeypatch)

    entrypoint.main()

    assert creds_path.read_text() == '{"refresh_token": "still-valid"}'
