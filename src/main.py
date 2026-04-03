import logging
import os
import sys

import yaml

from src.datasources.netatmo import NetatmoSource
from src.datasources.openweathermap import OpenWeatherMapSource
from src.renderer import render
from src.utils.fonts import FontRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

DATASOURCE_TYPES = {
    "netatmo": NetatmoSource,
    "openweathermap": OpenWeatherMapSource,
}


def _validate_subdir(base_dir: str, subdir: str, label: str) -> str:
    """Ensure a configured directory stays within base_dir (prevents path traversal)."""
    resolved = os.path.normpath(os.path.join(base_dir, subdir))
    if not resolved.startswith(os.path.normpath(base_dir) + os.sep):
        raise ValueError(f"{label} '{subdir}' escapes base directory")
    return resolved


def load_config(path: str = "config.yaml") -> dict:
    if not os.path.isfile(path):
        log.error("Config file not found: %s", path)
        sys.exit(1)
    with open(path) as f:
        return yaml.safe_load(f)


def fetch_all_data(config: dict) -> dict:
    """Instantiate all datasources and fetch their data."""
    all_data = {}
    timezone = config.get("timezone", "Europe/Berlin")

    for name, ds_config in config.get("datasources", {}).items():
        ds_type = ds_config["type"]
        cls = DATASOURCE_TYPES.get(ds_type)
        if cls is None:
            log.warning("Unknown datasource type '%s', skipping", ds_type)
            continue

        try:
            source = cls(ds_config, timezone=timezone)
            data = source.fetch()
            all_data[name] = data
            log.info("Fetched data from '%s': %s", name, list(data.keys()))
        except EnvironmentError as e:
            log.error("Configuration error for '%s': %s", name, e)
            all_data[name] = {}
        except Exception as e:
            log.error("Error fetching from '%s': %s", name, type(e).__name__)
            all_data[name] = {}

    return all_data


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    config = load_config(config_path)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fonts_dir = _validate_subdir(base_dir, config.get("fonts_dir", "fonts"), "fonts_dir")
    icons_dir = _validate_subdir(base_dir, config.get("icons_dir", "icons"), "icons_dir")

    fonts = FontRegistry(fonts_dir)
    all_data = fetch_all_data(config)

    img = render(config, all_data, fonts, icons_dir)

    output_file = config.get("output_file", "weather-script-output.png")
    img.save(output_file, "PNG")
    log.info("Output saved to %s", output_file)


if __name__ == "__main__":
    main()
