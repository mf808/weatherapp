import logging
import os
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from src.datasources.base import DataSource
from src.utils.config import resolve_env
from src.utils.http import safe_get

log = logging.getLogger(__name__)

CONDITION_MAPPING = {
    "01d": ".", "01n": "O",
    "02d": "#", "02n": "\u00a7",
    "03d": "b", "03n": "b",
    "04d": "4", "04n": "4",
    "09d": ":", "09n": ":",
    "10d": ")", "10n": "I",
    "11d": "/", "11n": "M",
    "13d": "<", "13n": "<",
    "50d": "B", "50n": "B",
}

MORNING_HOUR = 8
MIDDAY_HOUR = 13
EVENING_HOUR = 19
MAX_FORECAST_ENTRIES = 200  # 5 days * 8 slots = 40; cap well above


def _closest_entry(entries, target_hour):
    """Find the forecast entry whose hour is closest to target_hour."""
    best = None
    best_diff = 999
    for entry in entries:
        hour = entry["dt_obj"].hour
        diff = abs(hour - target_hour)
        if diff < best_diff:
            best_diff = diff
            best = entry
    return best


class OpenWeatherMapSource(DataSource):

    def __init__(self, config: dict, **kwargs):
        self.api_base = resolve_env(config["api_base"])
        self.app_id = resolve_env(config["app_id"])
        self.city_id = resolve_env(config["city_id"])

    def _fetch_current(self) -> dict:
        resp = safe_get(
            f"{self.api_base}/weather",
            params={
                "id": self.city_id,
                "lang": "en",
                "units": "metric",
                "APPID": self.app_id,
            },
        )
        data = resp.json()
        weather = data.get("weather", [])
        if not weather:
            return {"icon_code": "03d", "icon_glyph": "b", "description": "unknown"}
        icon_code = weather[0].get("icon", "03d")
        return {
            "icon_code": icon_code,
            "icon_glyph": CONDITION_MAPPING.get(icon_code, "b"),
            "description": weather[0].get("description", ""),
        }

    def _fetch_forecast(self) -> list[dict]:
        """Fetch 5-day/3-hour forecast and aggregate into daily summaries."""
        resp = safe_get(
            f"{self.api_base}/forecast",
            params={
                "id": self.city_id,
                "lang": "en",
                "units": "metric",
                "APPID": self.app_id,
            },
        )
        data = resp.json()

        entries_list = data.get("list", [])[:MAX_FORECAST_ENTRIES]
        if not entries_list:
            return []

        by_date = defaultdict(list)
        for entry in entries_list:
            try:
                dt = datetime.fromtimestamp(entry["dt"], tz=ZoneInfo(os.environ.get("TZ", "Europe/Berlin")))
            except (KeyError, TypeError, ValueError, OSError):
                continue
            date_key = dt.strftime("%Y-%m-%d")
            main = entry.get("main", {})
            weather = entry.get("weather", [{}])
            icon_code = weather[0].get("icon", "03d") if weather else "03d"
            by_date[date_key].append({
                "dt_obj": dt,
                "temp": main.get("temp", 0),
                "temp_min": main.get("temp_min", 0),
                "temp_max": main.get("temp_max", 0),
                "icon_code": icon_code,
                "icon_glyph": CONDITION_MAPPING.get(icon_code, "b"),
                "description": weather[0].get("description", "") if weather else "",
                "pop": entry.get("pop", 0),
            })

        today = datetime.now(tz=ZoneInfo(os.environ.get("TZ", "Europe/Berlin"))).strftime("%Y-%m-%d")
        all_dates = sorted(by_date.keys())
        start_dates = [d for d in all_dates if d >= today][:3]

        days = []
        for date_str in start_dates:
            entries = by_date[date_str]
            if not entries:
                continue

            day_min = min(e["temp_min"] for e in entries)
            day_max = max(e["temp_max"] for e in entries)
            rain_prob = max(e["pop"] for e in entries)

            morning = _closest_entry(entries, MORNING_HOUR)
            midday = _closest_entry(entries, MIDDAY_HOUR)
            evening = _closest_entry(entries, EVENING_HOUR)

            dt = datetime.strptime(date_str, "%Y-%m-%d")
            days.append({
                "date": date_str,
                "weekday": dt.strftime("%a"),
                "temp_min": f"{day_min:.0f}",
                "temp_max": f"{day_max:.0f}",
                "rain_prob": f"{rain_prob * 100:.0f}",
                "morning_icon": morning["icon_glyph"] if morning else "b",
                "midday_icon": midday["icon_glyph"] if midday else "b",
                "evening_icon": evening["icon_glyph"] if evening else "b",
                "morning_desc": morning["description"] if morning else "",
                "midday_desc": midday["description"] if midday else "",
                "evening_desc": evening["description"] if evening else "",
            })

        return days

    def fetch(self) -> dict:
        result = {}
        result["current"] = self._fetch_current()

        try:
            result["forecast"] = self._fetch_forecast()
        except requests.RequestException as e:
            # Log only the exception type: requests errors embed the full URL,
            # which carries the APPID secret as a query parameter.
            log.warning("Could not fetch forecast: %s", type(e).__name__)
            result["forecast"] = []

        return result
