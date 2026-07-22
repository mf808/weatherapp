"""Visual regression test — the rendered display must match a known-good golden PNG.

Determinism is engineered on both axes:
  * Inputs: a fixed fixture dataset (no network) fed through the *real* config.yaml
    layout, under a frozen clock (freezegun) so the watermark / datetime / chart
    x-axis labels don't move.
  * Comparison: a small per-pixel tolerance absorbs sub-pixel antialiasing (mainly
    from the matplotlib chart) while still catching any real layout/content change.

Regenerate the golden intentionally after a deliberate visual change:
    UPDATE_GOLDEN=1 python -m pytest tests/test_visual.py
"""

import os
from pathlib import Path

import numpy as np
import pytest
import yaml
from freezegun import freeze_time
from PIL import Image, ImageDraw

from src.renderer import render
from src.utils.image import apply_rotation

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN = REPO_ROOT / "tests" / "visual" / "golden" / "eink_landscape.png"
ARTIFACTS = REPO_ROOT / "tests" / "visual" / "_artifacts"

# Everything Pillow draws is bit-identical across machines (verified: 0.0000% diff
# WSL vs CI outside the chart). The matplotlib temperature chart is NOT pixel-portable
# — its scipy/BLAS spline math shifts antialiased edges by sub-pixel amounts across
# CPUs/builds — so its cell is masked out of the compare here and smoke-tested for
# non-emptiness in test_modules.py instead. That keeps this golden portable (runs
# anywhere) and the tolerance tight enough to catch real regressions.

# Frozen instant used for every render (TZ is pinned to UTC by conftest).
FROZEN_NOW = "2035-06-01 09:47:00"

# Tolerance: a pixel counts as "changed" if it differs by more than PIXEL_DELTA
# (out of 255); the test fails if more than MAX_CHANGED_FRACTION of the (non-chart)
# pixels changed. The non-chart region is bit-identical across machines, so this is
# deliberately tight.
PIXEL_DELTA = 12
MAX_CHANGED_FRACTION = 0.001  # 0.1%

# Fixed, representative data matching the source_keys referenced by config.yaml.
DATA = {
    "netatmo": {
        "outdoor": {
            "name": "Aussen", "temp": "12.3", "temp_trend": "down",
            "humidity": 78, "co2": "", "battery_status": "full", "pressure": 1013.2,
        },
        "outdoor_history": {
            "temperatures": [9.8, 10.1, 10.5, 11.0, 11.6, 12.0, 12.3, 12.1, 11.9, 12.4, 12.8, 13.0],
        },
        "Kinderzimmer": {
            "name": "Kinderzimmer", "temp": "21.4", "temp_trend": "stable",
            "co2": 640, "humidity": 47, "battery_status": "full",
        },
        "Elternzimmer": {  # co2 > 1200 -> "Lüften" branch
            "name": "Elternzimmer", "temp": "20.1", "temp_trend": "up",
            "co2": 1320, "humidity": 52, "battery_status": "half",
        },
        "Wohnzimmer": {  # humidity > 60 -> "Lüften" branch
            "name": "Wohnzimmer", "temp": "22.0", "temp_trend": "down",
            "co2": 700, "humidity": 63, "battery_status": "low",
        },
    },
    "openweathermap": {
        "current": {"icon_code": "10d", "icon_glyph": ")", "description": "light rain"},
        "forecast": [
            {"date": "2035-06-01", "weekday": "Fri", "temp_max": "21", "temp_min": "9",
             "rain_prob": "40", "midday_icon": ")"},
            {"date": "2035-06-02", "weekday": "Sat", "temp_max": "24", "temp_min": "12",
             "rain_prob": "10", "midday_icon": "."},
            {"date": "2035-06-03", "weekday": "Sun", "temp_max": "19", "temp_min": "11",
             "rain_prob": "70", "midday_icon": "4"},
        ],
    },
}


def _load_config() -> dict:
    with open(REPO_ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def _render(fonts, icons_dir) -> Image.Image:
    with freeze_time(FROZEN_NOW):
        return render(_load_config(), DATA, fonts, str(icons_dir))


def _chart_ignore_mask(config: dict) -> np.ndarray:
    """Boolean mask (True = ignore) over the temperature_chart cell, in final-image
    space. Built in device space from the layout geometry, then rotated the same way
    the renderer rotates the output so it lines up exactly."""
    dev = config["devices"][config["device"]]
    W, H, rot = dev["width"], dev["height"], dev.get("rotation")
    mask = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(mask)
    y = 0
    for row in config["layout"]["rows"]:
        rh = int(H * row["height"])
        x = 0
        for cell in row["cells"]:
            cw = int(W * cell["width"])
            if cell["module"] == "temperature_chart":
                draw.rectangle([x, y, x + cw - 1, y + rh - 1], fill=255)
            x += cw
        y += rh
    if rot:
        mask = apply_rotation(mask, rot)
    return np.asarray(mask) > 0


def test_display_matches_golden(fonts, icons_dir):
    img = _render(fonts, icons_dir)

    if os.environ.get("UPDATE_GOLDEN") or not GOLDEN.exists():
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        img.save(GOLDEN, "PNG")
        pytest.skip(f"golden written to {GOLDEN} — rerun without UPDATE_GOLDEN to compare")

    golden = Image.open(GOLDEN)
    assert (img.size, img.mode) == (golden.size, golden.mode), (
        f"render is {img.size}/{img.mode}, golden is {golden.size}/{golden.mode}"
    )

    a = np.asarray(img, dtype=np.int16)
    g = np.asarray(golden, dtype=np.int16)
    ignore = _chart_ignore_mask(_load_config())  # matplotlib cell is not pixel-portable
    changed = (np.abs(a - g) > PIXEL_DELTA) & ~ignore
    frac = float(changed.mean())

    if frac > MAX_CHANGED_FRACTION:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        img.save(ARTIFACTS / "actual.png", "PNG")
        Image.fromarray((changed * 255).astype("uint8")).save(ARTIFACTS / "diff_mask.png", "PNG")
        pytest.fail(
            f"{frac:.3%} of non-chart pixels changed (limit {MAX_CHANGED_FRACTION:.1%}). "
            f"Wrote {ARTIFACTS/'actual.png'} and {ARTIFACTS/'diff_mask.png'}. "
            f"If this change is intended, regenerate with UPDATE_GOLDEN=1."
        )
