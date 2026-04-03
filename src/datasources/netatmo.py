import json
import logging
import os
import stat
import time
from datetime import datetime

import requests

from src.datasources.base import DataSource
from src.utils.config import resolve_env
from src.utils.http import safe_get, safe_post

log = logging.getLogger(__name__)

# Battery voltage thresholds per module type
BATTERY_THRESHOLDS = {
    "NAModule1": [(5000, "full"), (4500, "half"), (4000, "low"), (0, "empty")],
    "NAModule4": [(5280, "full"), (4920, "half"), (4560, "low"), (0, "empty")],
}

CREDS_FILE_MODE = 0o600
MAX_CREDS_BYTES = 10 * 1024  # 10 KB — tokens should never be larger
MAX_MODULES = 50  # sanity cap on number of modules to process


def _battery_status(module_type: str, battery_vp: int) -> str:
    thresholds = BATTERY_THRESHOLDS.get(module_type)
    if not thresholds:
        return "full"
    for min_vp, status in thresholds:
        if battery_vp >= min_vp:
            return status
    return "empty"


def _safe_float(value, default: str = "--") -> str:
    """Safely format a value as float with 1 decimal."""
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return default


def _safe_timestamp(value, fmt: str = "%H:%M", default: str = "--") -> str:
    """Safely format a unix timestamp."""
    try:
        return datetime.fromtimestamp(int(value)).strftime(fmt)
    except (TypeError, ValueError, OSError):
        return default


class NetatmoSource(DataSource):

    def __init__(self, config: dict, timezone: str = "Europe/Berlin", **kwargs):
        self.api_base = resolve_env(config["api_base"])
        self.creds_file = config["creds_file"]
        self.device_id = resolve_env(config["device_id"])
        self.outdoor_module_id = resolve_env(config["outdoor_module_id"])
        self.client_id = resolve_env(config["client_id"])
        self.client_secret = resolve_env(config["client_secret"])
        self.history_scale = config.get("history_scale", "30min")
        self.history_limit = config.get("history_limit", 12)
        self.timezone = timezone
        self._access_token: str | None = None

    def _read_creds(self) -> dict:
        """Read credentials file with permission check."""
        if not os.path.isfile(self.creds_file):
            raise FileNotFoundError(f"Credentials file not found: {self.creds_file}")

        file_mode = os.stat(self.creds_file).st_mode
        if file_mode & (stat.S_IRGRP | stat.S_IROTH):
            try:
                os.chmod(self.creds_file, CREDS_FILE_MODE)
                log.info("Fixed credentials file permissions to 0600.")
            except OSError:
                log.warning("Credentials file %s is readable by group/others but chmod failed (mounted volume?).", self.creds_file)

        with open(self.creds_file) as f:
            creds = json.load(f)

        if "refresh_token" not in creds:
            raise ValueError("Credentials file missing 'refresh_token'")
        return creds

    def _write_creds(self, creds: dict):
        """Write credentials file with restricted permissions and size guard."""
        payload = json.dumps(creds, indent=4)
        if len(payload.encode()) > MAX_CREDS_BYTES:
            raise ValueError(f"Credentials payload too large ({len(payload)} bytes, max {MAX_CREDS_BYTES})")
        fd = os.open(self.creds_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, CREDS_FILE_MODE)
        with os.fdopen(fd, "w") as f:
            f.write(payload)

    def _refresh_tokens(self):
        creds = self._read_creds()
        resp = safe_post(
            f"{self.api_base}/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": creds["refresh_token"],
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        new_creds = resp.json()
        if not new_creds.get("access_token") or not new_creds.get("refresh_token"):
            raise RuntimeError("API did not return valid tokens")
        self._write_creds(new_creds)
        self._access_token = new_creds["access_token"]

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._access_token}",
        }

    def _fetch_devicelist(self) -> dict:
        resp = safe_get(
            f"{self.api_base}/api/devicelist",
            headers=self._headers(),
        )
        return resp.json()

    def _fetch_6h_history(self) -> list[float]:
        end = int(time.time())
        begin = end - 21600
        resp = safe_get(
            f"{self.api_base}/api/getmeasure",
            headers=self._headers(),
            params={
                "device_id": self.device_id,
                "module_id": self.outdoor_module_id,
                "scale": self.history_scale,
                "type": "temperature",
                "limit": self.history_limit,
                "date_begin": begin,
                "date_end": end,
            },
        )
        data = resp.json()
        body = data.get("body")
        if not body or not isinstance(body, list) or len(body) == 0:
            log.warning("6h history: empty or unexpected body")
            return []
        values = body[0].get("value", [])
        result = []
        for v in values:
            if isinstance(v, list) and len(v) > 0:
                try:
                    result.append(float(v[0]))
                except (TypeError, ValueError):
                    continue
        return result

    @staticmethod
    def _parse_dashboard(dash: dict | None) -> dict:
        """Extract common dashboard fields shared by base station and modules."""
        if not dash:
            return {
                "temp": "--", "temp_trend": None, "humidity": "--",
                "co2": "", "min_temp": "--", "min_time": "--",
                "max_temp": "--", "max_time": "--",
                "measure_time": "offline", "offline": True,
            }
        return {
            "temp": _safe_float(dash.get("Temperature")),
            "temp_trend": dash.get("temp_trend"),
            "humidity": dash.get("Humidity", "--"),
            "co2": dash.get("CO2", ""),
            "min_temp": _safe_float(dash.get("min_temp")),
            "min_time": _safe_timestamp(dash.get("date_min_temp")),
            "max_temp": _safe_float(dash.get("max_temp")),
            "max_time": _safe_timestamp(dash.get("date_max_temp")),
            "measure_time": _safe_timestamp(dash.get("time_utc")),
        }

    def _parse_module(self, mod: dict) -> dict:
        module_type = mod.get("type", "unknown")
        result = self._parse_dashboard(mod.get("dashboard_data"))
        result["name"] = mod.get("module_name", "Unknown")
        result["battery_status"] = _battery_status(module_type, mod.get("battery_vp", 9999))
        result["module_type"] = module_type
        return result

    def _parse_base(self, device: dict) -> dict:
        dash = device.get("dashboard_data")
        result = self._parse_dashboard(dash)
        result["name"] = device.get("module_name", "Base")
        result["battery_status"] = "charging"
        result["module_type"] = "base"
        if dash:
            result["pressure"] = dash.get("Pressure")
            result["pressure_trend"] = dash.get("pressure_trend")
        else:
            result["pressure"] = None
            result["pressure_trend"] = None
        return result

    def fetch(self) -> dict:
        self._refresh_tokens()

        devicelist = self._fetch_devicelist()
        body = devicelist.get("body", {})
        devices = body.get("devices", [])
        modules_raw = body.get("modules", [])[:MAX_MODULES]

        if not devices:
            log.warning("Netatmo: no devices found in response")
            return {"outdoor_history": {"temperatures": []}}

        result = {}

        base_data = self._parse_base(devices[0])
        result[base_data["name"]] = base_data

        outdoor_name = None
        for mod in modules_raw:
            parsed = self._parse_module(mod)
            result[parsed["name"]] = parsed
            if mod.get("type") == "NAModule1":
                outdoor_name = parsed["name"]

        if outdoor_name:
            result["outdoor"] = result[outdoor_name]

        try:
            temps = self._fetch_6h_history()
            result["outdoor_history"] = {"temperatures": temps}
        except requests.RequestException as e:
            log.warning("Could not fetch 6h history: %s", e)
            result["outdoor_history"] = {"temperatures": []}

        return result
