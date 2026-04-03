"""Lightweight HTTP server that generates the weather image on request.

GET /           → generates image, returns 200 with text status
GET /image      → generates image, returns the PNG directly
GET /health     → returns 200 OK
"""

import logging
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

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


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def generate(config: dict, fonts: FontRegistry, icons_dir: str) -> str:
    """Fetch data and render the image. Returns the output file path."""
    timezone = config.get("timezone", "Europe/Berlin")
    all_data = {}

    for name, ds_config in config.get("datasources", {}).items():
        ds_type = ds_config["type"]
        cls = DATASOURCE_TYPES.get(ds_type)
        if cls is None:
            continue
        try:
            source = cls(ds_config, timezone=timezone)
            all_data[name] = source.fetch()
            log.info("Fetched data from '%s'", name)
        except Exception as e:
            log.error("Error fetching from '%s': %s", name, type(e).__name__)
            all_data[name] = {}

    img = render(config, all_data, fonts, icons_dir)
    output_file = config.get("output_file", "weather-script-output.png")
    img.save(output_file, "PNG")
    log.info("Output saved to %s", output_file)
    return output_file


class WeatherHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
            return

        if self.path == "/image":
            try:
                output_file = generate(self.server.config, self.server.fonts, self.server.icons_dir)
                with open(output_file, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                log.error("Generation failed: %s", type(e).__name__)
                self.send_response(500)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Error generating image")
            return

        # Default: generate and return status text (backwards compatible with curl trigger)
        try:
            generate(self.server.config, self.server.fonts, self.server.icons_dir)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Image generated successfully")
        except Exception as e:
            log.error("Generation failed: %s", type(e).__name__)
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Error generating image")

    def log_message(self, format, *args):
        # Suppress default access logs, we use our own logging
        pass


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    config = load_config(config_path)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fonts_dir = os.path.join(base_dir, config.get("fonts_dir", "fonts"))
    icons_dir = os.path.join(base_dir, config.get("icons_dir", "icons"))

    port = int(config.get("port", 8080))
    fonts = FontRegistry(fonts_dir)

    server = HTTPServer(("0.0.0.0", port), WeatherHandler)
    server.config = config
    server.fonts = fonts
    server.icons_dir = icons_dir

    log.info("Weather server listening on port %d", port)
    log.info("  GET /       → generate image, return status")
    log.info("  GET /image  → generate image, return PNG")
    log.info("  GET /health → health check")
    server.serve_forever()


if __name__ == "__main__":
    main()
