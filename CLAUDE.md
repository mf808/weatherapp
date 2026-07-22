# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Modular weather display for e-ink screens. Fetches data from Netatmo (indoor/outdoor sensors) and OpenWeatherMap (current + forecast), then renders a grayscale PNG whose layout is fully driven by `config.yaml`. This is a Python rewrite of an original PHP script — much of the code carries PHP-compatibility scaling (see Font/DPI notes below).

## Commands

Local development (env vars must be set; see `datasources` in `config.yaml` for the full list):
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export CLIENT_ID=... CLIENT_SECRET=... DEVICE_ID=... OUTDOOMODULE_ID=... OPENWEATHERMAP_APPID=...

python -m src.main      # one-shot: writes weather-script-output.png and exits
python -m src.server    # HTTP server on port 8080 (see config.yaml `port`)
```

Both entrypoints accept an optional config path as `argv[1]` (defaults to `config.yaml`).

Docker:
```bash
docker-compose build && docker-compose up -d
docker-compose build --no-cache && docker-compose up -d   # force update
docker logs app_weather
```

Tests (pytest, in `tests/`):
```bash
pip install -r requirements-dev.txt
python -m pytest              # whole suite
python -m pytest tests/test_netatmo.py -q      # one file
python -m pytest -k battery                     # by keyword
```
Tests are static and repeatable: no network (all HTTP is monkeypatched at the
`src.utils.http` boundary via a `FakeResponse` in `conftest.py`), and `conftest.py`
pins `TZ=UTC` (autouse) so timestamp/date logic is deterministic on any host. Datasource
tests use fixed future timestamps (year 2035) to stay clear of the forecast's `>= today`
filter. CI runs the suite on every PR (`.github/workflows/ci.yml`); no linter is configured.

## Development workflow (non-negotiable)

This repo deploys itself: a push to `main` auto-versions, builds a Docker image, and
publishes it to GHCR (`ghcr.io/mf808/weatherapp`), where Watchtower on the NAS picks it
up. To keep `main` — and therefore the `latest` image and the physical display — always
green, **every change goes through a gated PR. Never push to `main` directly** (branch
protection enforces this server-side too).

For any code change:
1. Branch off `main`: `git switch -c <type>/<slug>`.
2. Implement, then run `python -m pytest` locally.
3. Push the branch and open a PR whose **title is a Conventional Commit** — this drives
   the version bump: `fix:` → patch, `feat:` → minor, `feat!:` / `BREAKING CHANGE` → major.
4. `.github/workflows/ci.yml` runs the suite on the PR; branch protection blocks merge
   until it is green.
5. **Squash-merge.** `.github/workflows/release.yml` then tags `vX.Y.Z`, builds, and pushes
   `ghcr.io/mf808/weatherapp:vX.Y.Z` + `:latest`, and cuts a GitHub Release.

Versions are derived automatically from commit messages — write Conventional-Commits
titles and **never hand-edit a version number**. Deploy is hands-off (Watchtower). The one
deliberate manual action is **rollback**: pin a known-good tag on the NAS with
`./rollback.sh v1.4.0` (or set `image: ...:v1.4.0` in `deploy/docker-compose.yaml` and
`docker compose up -d`).

## Architecture

The pipeline is: **config → fetch all datasources → render layout grid → post-process image → save PNG**. Orchestrated identically by `src/main.py` (one-shot) and `src/server.py` (HTTP), which each hold their own copy of this loop plus a `DATASOURCE_TYPES` registry.

**Datasources** (`src/datasources/`) implement `DataSource.fetch() -> dict` (base in `base.py`). Each returns a dict keyed by sensor/data name (e.g. Netatmo returns `outdoor`, `outdoor_history`, and one entry per room like `Kinderzimmer`). Registered in the `DATASOURCE_TYPES` dict in *both* `main.py` and `server.py` — add a new source in both places. All fetch errors are caught and degrade to `{}` so a single failing source never breaks the render.

**Modules** (`src/modules/`) implement `Module.render(...) -> PIL.Image` (base in `base.py`) and draw one grid cell. Registered in `MODULE_REGISTRY` in `src/renderer.py`. Existing modules: `outdoor`, `room_climate`, `temperature_chart`, `forecast`, `datetime_info`.

**Renderer** (`src/renderer.py`) walks `config.layout.rows[].cells[]`, using proportional `height`/`width` (0.0–1.0) to size each cell. For each cell it looks up `all_data[source][source_key]` to get that cell's data, instantiates the module by name, and pastes the result. Also draws the timestamp watermark and applies device post-processing (rotation, grayscale) at the end.

### Configuration model

`config.yaml` is the single source of truth for layout and wiring. `device:` picks one profile from `devices:` (dimensions, rotation, grayscale). Secrets and deployment values use `${ENV_VAR}` / `${ENV_VAR:-default}` syntax, resolved by `src/utils/config.py:resolve_env` — datasources call `resolve_env()` on each field in their `__init__`. A required `${VAR}` with no value raises `EnvironmentError`. Note: config is copied into the data folder for deployment (see README), so `config.yaml` in the repo is both the default and the template.

### Conventions specific to this codebase

- **PHP DPI compatibility**: `FontRegistry.scaled()` (`src/utils/fonts.py`) multiplies point sizes by `96/72` because the original PHP GD rendered at 96 DPI and Pillow uses 72. Use `fonts.scaled(name, php_size)` when porting sizes from the old layout. `constants.py` `cell_scale()` similarly scales against the original 266×300 PHP cell.
- **Timezone**: read from the `TZ` env var (defaults to `Europe/Berlin`) via `zoneinfo`, set in Docker. Timestamps in `renderer.py` and `netatmo.py` depend on this.
- **Network calls** go through `src/utils/http.py` `safe_get`/`safe_post`, which enforce connect/read timeouts and a 5 MB response cap. Prefer these over raw `requests`.
- **Netatmo tokens**: `creds.json` holds `access_token`/`refresh_token`, refreshed on every `fetch()`. The file is rewritten with `0600` perms and a size guard; chmod failures are non-fatal to support read-only-ish Docker mounts.
- **e-ink output**: PNGs are saved as 8-bit grayscale (mode `L`) via `src/utils/image.py`; keep this when touching output code (e-ink displays need it).

### HTTP endpoints (`src/server.py`)

`GET /` triggers generation and returns status text; `GET /weather-script-output.png` serves the last PNG (backwards-compatible with the old wget-based cron workflow); `GET /image` generates and returns the PNG in one request; `GET /health` is a health check.
