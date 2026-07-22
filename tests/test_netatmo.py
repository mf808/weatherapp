import json

import pytest

from conftest import FakeResponse
from src.datasources import netatmo
from src.datasources.netatmo import (
    NetatmoSource,
    _battery_status,
    _safe_float,
    _safe_timestamp,
)


# ── _battery_status ─────────────────────────────────────────────

@pytest.mark.parametrize("vp,expected", [
    (5200, "full"),
    (5000, "full"),   # boundary — inclusive
    (4999, "half"),
    (4500, "half"),   # boundary
    (4499, "low"),
    (4000, "low"),    # boundary
    (3999, "empty"),
    (0, "empty"),
])
def test_battery_status_namodule1_thresholds(vp, expected):
    assert _battery_status("NAModule1", vp) == expected


def test_battery_status_namodule4_scale_differs():
    # NAModule4 uses a higher voltage scale than NAModule1.
    assert _battery_status("NAModule4", 5280) == "full"
    assert _battery_status("NAModule4", 4560) == "low"


def test_battery_status_unknown_type_defaults_full():
    assert _battery_status("NAModuleUnknown", 100) == "full"


def test_battery_status_negative_is_empty():
    assert _battery_status("NAModule1", -1) == "empty"


# ── _safe_float ─────────────────────────────────────────────────

@pytest.mark.parametrize("value,expected", [
    (20, "20.0"),
    (12.34, "12.3"),
    ("3.14159", "3.1"),
    (-5.0, "-5.0"),
    (0, "0.0"),
])
def test_safe_float_formats(value, expected):
    assert _safe_float(value) == expected


@pytest.mark.parametrize("value", [None, "abc", "", [1, 2]])
def test_safe_float_invalid_returns_default(value):
    assert _safe_float(value) == "--"


def test_safe_float_custom_default():
    assert _safe_float(None, default="n/a") == "n/a"


# ── _safe_timestamp (TZ pinned to UTC by conftest) ──────────────

def test_safe_timestamp_epoch():
    assert _safe_timestamp(0) == "00:00"


def test_safe_timestamp_known_value():
    # 1970-01-01 01:30:00 UTC
    assert _safe_timestamp(5400) == "01:30"


@pytest.mark.parametrize("value", [None, "not-a-number", []])
def test_safe_timestamp_invalid_returns_default(value):
    assert _safe_timestamp(value) == "--"


def test_safe_timestamp_custom_format():
    assert _safe_timestamp(0, fmt="%Y-%m-%d") == "1970-01-01"


# ── _parse_dashboard ────────────────────────────────────────────

def test_parse_dashboard_none_is_offline():
    d = NetatmoSource._parse_dashboard(None)
    assert d["offline"] is True
    assert d["temp"] == "--"
    assert d["measure_time"] == "offline"


def test_parse_dashboard_populated():
    d = NetatmoSource._parse_dashboard({
        "Temperature": 21.5, "Humidity": 45, "CO2": 600,
        "temp_trend": "up", "time_utc": 0,
        "min_temp": 18.2, "date_min_temp": 0,
        "max_temp": 24.9, "date_max_temp": 5400,
    })
    assert d["temp"] == "21.5"
    assert d["humidity"] == 45
    assert d["temp_trend"] == "up"
    assert d["max_time"] == "01:30"
    assert "offline" not in d


# ── fetch() integration with mocked HTTP + creds file ───────────

@pytest.fixture
def creds_file(tmp_path):
    p = tmp_path / "creds.json"
    p.write_text(json.dumps({
        "access_token": "old-access",
        "refresh_token": "old-refresh",
    }))
    return p


def _source(creds_file):
    return NetatmoSource({
        "api_base": "https://api.example.com",
        "creds_file": str(creds_file),
        "device_id": "dev-1",
        "outdoor_module_id": "mod-1",
        "client_id": "cid",
        "client_secret": "csecret",
    })


DEVICELIST = {
    "body": {
        "devices": [{
            "module_name": "Base",
            "dashboard_data": {
                "Temperature": 21.5, "Humidity": 45, "CO2": 600,
                "Pressure": 1013.2, "pressure_trend": "up", "time_utc": 0,
            },
        }],
        "modules": [{
            "type": "NAModule1",
            "module_name": "Outdoor",
            "battery_vp": 5200,
            "dashboard_data": {
                "Temperature": 12.3, "Humidity": 80,
                "temp_trend": "down", "time_utc": 0,
            },
        }],
    }
}

HISTORY = {"body": [{"value": [[10.0], [10.5], [11.0]]}]}


def _install_http(monkeypatch, *, devicelist=DEVICELIST, history=HISTORY):
    def fake_post(url, **kwargs):
        return FakeResponse({"access_token": "new-access", "refresh_token": "new-refresh"})

    def fake_get(url, **kwargs):
        if "devicelist" in url:
            return FakeResponse(devicelist)
        if "getmeasure" in url:
            return FakeResponse(history)
        raise AssertionError(f"unexpected GET {url}")

    monkeypatch.setattr(netatmo, "safe_post", fake_post)
    monkeypatch.setattr(netatmo, "safe_get", fake_get)


def test_fetch_returns_all_sensors(monkeypatch, creds_file):
    _install_http(monkeypatch)
    result = _source(creds_file).fetch()

    assert result["Base"]["pressure"] == 1013.2
    assert result["Outdoor"]["temp"] == "12.3"
    assert result["Outdoor"]["battery_status"] == "full"
    # NAModule1 is aliased to the generic 'outdoor' key used by the layout.
    assert result["outdoor"] == result["Outdoor"]
    assert result["outdoor_history"]["temperatures"] == [10.0, 10.5, 11.0]


def test_fetch_refreshes_and_persists_tokens(monkeypatch, creds_file):
    _install_http(monkeypatch)
    _source(creds_file).fetch()
    saved = json.loads(creds_file.read_text())
    assert saved == {"access_token": "new-access", "refresh_token": "new-refresh"}


def test_fetch_handles_no_devices(monkeypatch, creds_file):
    _install_http(monkeypatch, devicelist={"body": {"devices": [], "modules": []}})
    result = _source(creds_file).fetch()
    assert result == {"outdoor_history": {"temperatures": []}}


def test_fetch_handles_empty_history_body(monkeypatch, creds_file):
    _install_http(monkeypatch, history={"body": []})
    result = _source(creds_file).fetch()
    assert result["outdoor_history"]["temperatures"] == []


def test_fetch_skips_malformed_history_points(monkeypatch, creds_file):
    _install_http(monkeypatch, history={"body": [{"value": [[10.0], [], ["bad"], [11.0]]}]})
    result = _source(creds_file).fetch()
    assert result["outdoor_history"]["temperatures"] == [10.0, 11.0]


# ── credentials handling edge cases ─────────────────────────────

def test_refresh_rejects_missing_tokens(monkeypatch, creds_file):
    def fake_post(url, **kwargs):
        return FakeResponse({"access_token": "only-access"})  # no refresh_token
    monkeypatch.setattr(netatmo, "safe_post", fake_post)
    with pytest.raises(RuntimeError):
        _source(creds_file)._refresh_tokens()


def test_read_creds_missing_file_raises(tmp_path):
    src = _source(tmp_path / "nope.json")
    with pytest.raises(FileNotFoundError):
        src._read_creds()


def test_read_creds_missing_refresh_token_raises(tmp_path):
    p = tmp_path / "creds.json"
    p.write_text(json.dumps({"access_token": "x"}))
    with pytest.raises(ValueError, match="refresh_token"):
        _source(p)._read_creds()


def test_write_creds_rejects_oversized_payload(creds_file):
    src = _source(creds_file)
    with pytest.raises(ValueError, match="too large"):
        src._write_creds({"refresh_token": "x" * (netatmo.MAX_CREDS_BYTES + 1)})


def test_write_creds_new_file_is_restrictive(tmp_path):
    """A freshly created creds file is written with 0600 (O_CREAT mode)."""
    import stat
    target = tmp_path / "fresh.json"  # does not exist yet
    _source(target)._write_creds({"access_token": "a", "refresh_token": "b"})
    assert stat.S_IMODE(target.stat().st_mode) == netatmo.CREDS_FILE_MODE  # 0o600


def test_read_creds_tightens_loose_permissions(tmp_path):
    """A group/world-readable creds file is chmod-ed back to 0600 on read."""
    import os
    import stat
    p = tmp_path / "creds.json"
    p.write_text(json.dumps({"refresh_token": "r"}))
    os.chmod(p, 0o644)
    _source(p)._read_creds()
    assert stat.S_IMODE(p.stat().st_mode) == netatmo.CREDS_FILE_MODE  # 0o600
