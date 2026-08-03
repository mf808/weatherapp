"""End-to-end render test: config + data -> post-processed image."""

from PIL import Image

from src.renderer import MODULE_REGISTRY, render

CONFIG = {
    "device": "eink_landscape",
    "devices": {
        "eink_landscape": {"width": 800, "height": 600, "rotation": 90, "grayscale": True},
        "tablet": {"width": 1024, "height": 768, "rotation": 0, "grayscale": False},
    },
    "layout": {
        "rows": [
            {"height": 0.5, "background": "white", "cells": [
                {"width": 0.34, "module": "outdoor", "source": "netatmo", "source_key": "outdoor",
                 "params": {"weather_source": "owm", "weather_key": "current"}},
                {"width": 0.33, "module": "temperature_chart", "source": "netatmo", "source_key": "outdoor_history"},
                {"width": 0.33, "module": "forecast", "params": {"forecast_source": "owm"}},
            ]},
            {"height": 0.5, "background": "black", "cells": [
                {"width": 0.5, "module": "room_climate", "source": "netatmo", "source_key": "Kinderzimmer"},
                {"width": 0.5, "module": "datetime_info"},
            ]},
        ]
    },
}

DATA = {
    "netatmo": {
        "outdoor": {"name": "Out", "temp": "12.3", "temp_trend": "up", "humidity": 70,
                    "battery_status": "full", "pressure": 1013.2},
        "outdoor_history": {"temperatures": [10.0, 10.5, 11.0]},
        "Kinderzimmer": {"name": "Kind", "temp": "21.0", "co2": 500, "humidity": 45,
                         "battery_status": "full"},
    },
    "owm": {
        "current": {"icon_glyph": ")"},
        "forecast": [{"date": "2035-06-01", "weekday": "Fri", "temp_max": "20",
                      "temp_min": "8", "rain_prob": "40", "midday_icon": ")"}],
    },
}


def test_render_landscape_rotates_and_greyscales(fonts, icons_dir):
    img = render(CONFIG, DATA, fonts, icons_dir)
    # 90° rotation of 800x600 swaps to 600x800...
    assert img.size == (600, 800)
    # ...and the e-ink profile forces 8-bit grayscale.
    assert img.mode == "L"


def test_render_tablet_no_rotation_rgb(fonts, icons_dir):
    cfg = dict(CONFIG, device="tablet")
    img = render(cfg, DATA, fonts, icons_dir)
    assert img.size == (1024, 768)
    assert img.mode == "RGB"


def test_render_tolerates_missing_data(fonts, icons_dir):
    """Every datasource returned {} (fetch failure) — render must still produce an image."""
    img = render(CONFIG, {}, fonts, icons_dir)
    assert img.size == (600, 800)


def test_render_unknown_module_is_skipped(fonts, icons_dir):
    cfg = {
        "device": "tablet",
        "devices": {"tablet": {"width": 400, "height": 200, "rotation": 0, "grayscale": False}},
        "layout": {"rows": [{"height": 1.0, "background": "white", "cells": [
            {"width": 1.0, "module": "does_not_exist"},
        ]}]},
    }
    img = render(cfg, {}, fonts, icons_dir)
    assert img.size == (400, 200)


def test_render_shows_stale_banner_when_netatmo_data_is_marked_stale(fonts, icons_dir):
    data_stale = {**DATA, "netatmo": {**DATA["netatmo"], "_stale": {"as_of": 0}}}
    img_fresh = render(CONFIG, DATA, fonts, icons_dir)
    img_stale = render(CONFIG, data_stale, fonts, icons_dir)
    assert img_fresh.tobytes() != img_stale.tobytes()


def test_render_stale_banner_survives_missing_as_of(fonts, icons_dir):
    """A malformed/missing 'as_of' must not crash the render - falls back to '?'."""
    data_stale = {**DATA, "netatmo": {**DATA["netatmo"], "_stale": {}}}
    img = render(CONFIG, data_stale, fonts, icons_dir)
    assert img.size == (600, 800)


def test_render_stale_without_chart_cell_does_not_crash(fonts, icons_dir):
    """A layout with no temperature_chart cell has nowhere to anchor the banner -
    must render normally instead of crashing (chart_cell_bounds stays None)."""
    cfg = {
        **CONFIG,
        "layout": {"rows": [{"height": 1.0, "background": "white", "cells": [
            {"width": 1.0, "module": "outdoor", "source": "netatmo", "source_key": "outdoor"},
        ]}]},
    }
    data_stale = {**DATA, "netatmo": {**DATA["netatmo"], "_stale": {"as_of": 0}}}
    img = render(cfg, data_stale, fonts, icons_dir)
    assert img.size == (600, 800)


def test_all_registered_modules_are_importable():
    # Guards against a registry entry pointing at a missing/renamed class.
    assert set(MODULE_REGISTRY) == {
        "outdoor", "room_climate", "temperature_chart", "datetime_info", "forecast",
    }
    for cls in MODULE_REGISTRY.values():
        assert hasattr(cls, "render")
