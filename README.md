# weatherapp

Modular weather display for e-ink screens. Fetches data from Netatmo and OpenWeatherMap, renders a grayscale PNG with configurable layout.

## Architecture

```
src/
  server.py              # HTTP server (trigger + serve PNG)
  main.py                # CLI one-shot mode
  renderer.py            # Grid engine + module registry
  datasources/           # Netatmo, OpenWeatherMap
  modules/               # outdoor, room_climate, forecast, temperature_chart, datetime_info
  utils/                 # colors, config, fonts, http, image
config.yaml              # Layout, device profiles, datasource config
```

## Prerequisites

- Netatmo account with API credentials: <https://dev.netatmo.com/apps/>
- OpenWeatherMap free API key: <https://openweathermap.org/api>

## Setup

### 1. Create a data folder

```bash
mkdir -p /path/to/data
```

### 2. Create `creds.json`

Get initial tokens from <https://dev.netatmo.com/apps/> and create the file in your data folder:

```json
{
    "access_token": "XXXXXXXXXXXXXXXXXXXXXXXXX|XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "refresh_token": "XXXXXXXXXXXXXXXXXXXXXXXXX|XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
}
```

Tokens are automatically refreshed on every run.

### 3. Copy `config.yaml`

Copy `config.yaml` from this repo into your data folder. This controls the display layout, device profiles, and datasource settings. Edit it to match your setup:

```bash
cp config.yaml /path/to/data/config.yaml
```

Key things to configure:
- `device:` — select a device profile (`eink_landscape`, `eink_portrait`, `tablet`)
- `layout:` — rearrange modules, change grid proportions
- `datasources.netatmo.history_scale` / `history_limit` — chart data resolution

### 4. Create empty output/cache files

```bash
touch /path/to/data/weather-script-output.png
touch /path/to/data/last_good_netatmo.json
```

`last_good_netatmo.json` caches the last successful Netatmo reading (up to 6h old) so a
temporary API hiccup shows a "stale data" banner instead of blanking the display to zero.

## Docker Deployment

The image builds directly from GitHub — no local clone needed.

```yaml
services:
  weather:
    build: https://github.com/mf808/weatherapp.git#main
    container_name: weather
    restart: unless-stopped
    volumes:
      - /path/to/data/config.yaml:/app/config.yaml:ro
      - /path/to/data/creds.json:/app/creds.json:rw
      - /path/to/data/last_good_netatmo.json:/app/last_good_netatmo.json:rw
      - /path/to/data/weather-script-output.png:/app/weather-script-output.png:rw
    ports:
      - 81:8080
    environment:
      - CLIENT_ID=your_netatmo_client_id
      - CLIENT_SECRET=your_netatmo_client_secret
      - DEVICE_ID=XX:XX:XX:XX:XX:XX
      - OUTDOOMODULE_ID=XX:XX:XX:XX:XX:XX
      - OPENWEATHERMAP_APPID=your_openweathermap_key
    mem_limit: 128M
    mem_reservation: 64M
```

### Build and start

```bash
docker-compose build && docker-compose up -d
```

### Update to latest version

```bash
docker-compose build --no-cache && docker-compose up -d
```

## HTTP Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Trigger image generation, returns `200` with status text |
| `GET /weather-script-output.png` | Download the last generated PNG |
| `GET /image` | Generate and return PNG in one request |
| `GET /health` | Health check |

### Typical usage (e.g. from cron)

```bash
curl http://hostname:81/                              # trigger
wget -O display.png http://hostname:81/weather-script-output.png  # download
```

## Local Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export CLIENT_ID=... CLIENT_SECRET=... DEVICE_ID=... OUTDOOMODULE_ID=... OPENWEATHERMAP_APPID=...
python -m src.main          # one-shot: generates weather-script-output.png
python -m src.server        # HTTP server on port 8080
```

## Layout Customization

Edit `config.yaml` to rearrange the display. The layout uses proportional sizes (0.0-1.0):

```yaml
layout:
  rows:
    - height: 0.5
      background: white
      cells:
        - width: 0.33
          module: outdoor
          source: netatmo
          source_key: outdoor
```

Available modules: `outdoor`, `room_climate`, `temperature_chart`, `forecast`, `datetime_info`

To add a new Netatmo sensor, add a `room_climate` cell with the sensor's name as `source_key`.

## Troubleshooting

- **Stale image**: check that the cron/trigger is running and hitting `GET /`
- **Expired tokens**: recreate at <https://dev.netatmo.com/apps/> and update `creds.json`
- **Sensor offline**: if a module shows `--`, the sensor has lost connection to the base station (check battery/RF signal)
- **"Stand HH:MM" banner** (black bar under the 6h chart): the current Netatmo fetch failed (rate limit, timeout, brief API outage) and the display fell back to the last successful reading (up to 6h old, see `NetatmoSource._fallback()`). Check `docker logs weather` for the specific failed step (token refresh / stations data / 6h history) and HTTP status — if it clears up on its own within a few cycles, no action needed. If it persists past 6h, the display reverts to honest `--`/"Keine Daten" instead of showing an increasingly stale reading.
- **Container logs**: `docker logs weather`
