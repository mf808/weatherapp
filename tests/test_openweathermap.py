from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from conftest import FakeResponse
from src.datasources import openweathermap
from src.datasources.openweathermap import OpenWeatherMapSource, _closest_entry

UTC = ZoneInfo("UTC")


def _entry(hour):
    return {"dt_obj": datetime(2035, 6, 1, hour, tzinfo=UTC)}


# ── _closest_entry ──────────────────────────────────────────────

def test_closest_entry_exact_match():
    entries = [_entry(6), _entry(13), _entry(19)]
    assert _closest_entry(entries, 13) is entries[1]


def test_closest_entry_nearest_when_no_exact():
    entries = [_entry(6), _entry(12), _entry(18)]
    assert _closest_entry(entries, 13) is entries[1]  # |12-13|=1 wins


def test_closest_entry_empty_returns_none():
    assert _closest_entry([], 8) is None


# ── fetch() with fixed future timestamps (survives the >= today filter) ──

def _ts(year, month, day, hour):
    return int(datetime(year, month, day, hour, tzinfo=UTC).timestamp())


def _fc_entry(hour, tmin, tmax, pop, icon):
    return {
        "dt": _ts(2035, 6, 1, hour),
        "main": {"temp": (tmin + tmax) / 2, "temp_min": tmin, "temp_max": tmax},
        "weather": [{"icon": icon, "description": f"desc-{icon}"}],
        "pop": pop,
    }


def _source():
    return OpenWeatherMapSource({
        "api_base": "https://owm.example.com",
        "app_id": "key",
        "city_id": "123",
    })


def _install(monkeypatch, *, current, forecast):
    def fake_get(url, **kwargs):
        if url.endswith("/weather"):
            return FakeResponse(current)
        if url.endswith("/forecast"):
            return FakeResponse(forecast)
        raise AssertionError(f"unexpected GET {url}")
    monkeypatch.setattr(openweathermap, "safe_get", fake_get)


CURRENT = {"weather": [{"icon": "04d", "description": "broken clouds"}]}
FORECAST = {"list": [
    _fc_entry(6, 8, 12, 0.1, "01d"),
    _fc_entry(12, 14, 20, 0.4, "10d"),
    _fc_entry(18, 11, 16, 0.2, "01n"),
]}


def test_fetch_current_maps_icon_glyph(monkeypatch):
    _install(monkeypatch, current=CURRENT, forecast={"list": []})
    result = _source().fetch()
    assert result["current"]["icon_code"] == "04d"
    assert result["current"]["icon_glyph"] == "4"
    assert result["current"]["description"] == "broken clouds"


def test_fetch_current_empty_weather_uses_fallback(monkeypatch):
    _install(monkeypatch, current={"weather": []}, forecast={"list": []})
    result = _source().fetch()
    assert result["current"] == {"icon_code": "03d", "icon_glyph": "b", "description": "unknown"}


def test_fetch_current_unknown_icon_falls_back_to_b(monkeypatch):
    _install(monkeypatch, current={"weather": [{"icon": "99z"}]}, forecast={"list": []})
    assert _source().fetch()["current"]["icon_glyph"] == "b"


def test_fetch_forecast_aggregates_day(monkeypatch):
    _install(monkeypatch, current=CURRENT, forecast=FORECAST)
    days = _source().fetch()["forecast"]
    assert len(days) == 1
    day = days[0]
    assert day["date"] == "2035-06-01"
    assert day["temp_max"] == "20"       # max of temp_max across the day
    assert day["temp_min"] == "8"        # min of temp_min across the day
    assert day["rain_prob"] == "40"      # max pop * 100, rounded
    assert day["morning_icon"] == "."    # closest to 08:00 -> the 06:00 entry (01d)
    assert day["midday_icon"] == ")"     # closest to 13:00 -> the 12:00 entry (10d)
    assert day["evening_icon"] == "O"    # closest to 19:00 -> the 18:00 entry (01n)


def test_fetch_forecast_empty_list(monkeypatch):
    _install(monkeypatch, current=CURRENT, forecast={"list": []})
    assert _source().fetch()["forecast"] == []


def test_fetch_forecast_skips_entries_without_dt(monkeypatch):
    bad = {"list": [{"main": {}, "weather": [{}]}, _fc_entry(12, 14, 20, 0.3, "01d")]}
    _install(monkeypatch, current=CURRENT, forecast=bad)
    days = _source().fetch()["forecast"]
    assert len(days) == 1  # malformed entry dropped, valid one aggregated
