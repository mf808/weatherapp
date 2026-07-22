"""Render smoke tests for each display module.

These assert structural invariants (a correctly sized RGB image is produced) and
exercise the notable branches, rather than pixel-comparing, so they stay stable
across Pillow/matplotlib versions while still catching crashes and regressions.
"""

import pytest
from PIL import Image

from src.modules.datetime_info import DateTimeModule
from src.modules.forecast import ForecastModule
from src.modules.outdoor import OutdoorModule
from src.modules.room_climate import RoomClimateModule
from src.modules.temperature_chart import TemperatureChartModule

W, H = 266, 300


def _assert_cell(img):
    assert isinstance(img, Image.Image)
    assert img.size == (W, H)
    assert img.mode == "RGB"


@pytest.mark.parametrize("background", ["white", "black"])
def test_datetime_module(fonts, icons_dir, background):
    img = DateTimeModule().render(W, H, {}, fonts, icons_dir, background=background)
    _assert_cell(img)


@pytest.mark.parametrize("background", ["white", "black"])
def test_outdoor_module_full(fonts, icons_dir, background):
    data = {"name": "Outside", "temp": "12.3", "temp_trend": "down",
            "humidity": 80, "battery_status": "half"}
    all_data = {"netatmo": {"Base": {"pressure": 1013.2}},
                "owm": {"current": {"icon_glyph": ")"}}}
    params = {"weather_source": "owm", "weather_key": "current"}
    img = OutdoorModule().render(W, H, data, fonts, icons_dir,
                                 background=background, params=params, all_data=all_data)
    _assert_cell(img)


def test_outdoor_module_empty_data(fonts, icons_dir):
    _assert_cell(OutdoorModule().render(W, H, {}, fonts, icons_dir))


def test_outdoor_module_long_temp_shifts_layout(fonts, icons_dir):
    """temp strings longer than 4 chars take the shifted-x branch."""
    _assert_cell(OutdoorModule().render(W, H, {"temp": "-10.5"}, fonts, icons_dir))


def test_outdoor_module_offline_no_humidity(fonts, icons_dir):
    _assert_cell(OutdoorModule().render(W, H, {"humidity": ""}, fonts, icons_dir))


@pytest.mark.parametrize("background", ["white", "black"])
def test_room_climate_good_air(fonts, icons_dir, background):
    data = {"name": "Kinderzimmer", "temp": "21.0", "temp_trend": "stable",
            "co2": 500, "humidity": 45, "battery_status": "full"}
    _assert_cell(RoomClimateModule().render(W, H, data, fonts, icons_dir, background=background))


def test_room_climate_ventilate_on_high_co2(fonts, icons_dir):
    # co2 > 1200 triggers the "Lüften" branch
    data = {"name": "X", "co2": 1500, "humidity": 40}
    _assert_cell(RoomClimateModule().render(W, H, data, fonts, icons_dir))


def test_room_climate_ventilate_on_high_humidity(fonts, icons_dir):
    # humidity > 60 also triggers "Lüften"
    _assert_cell(RoomClimateModule().render(W, H, {"co2": 400, "humidity": 75}, fonts, icons_dir))


def test_room_climate_empty_and_nonnumeric(fonts, icons_dir):
    # non-numeric co2/humidity must be coerced without crashing
    _assert_cell(RoomClimateModule().render(W, H, {"co2": "", "humidity": "--"}, fonts, icons_dir))


def test_temperature_chart_no_data(fonts, icons_dir):
    _assert_cell(TemperatureChartModule().render(W, H, {"temperatures": []}, fonts, icons_dir))


def test_temperature_chart_single_point_is_no_data(fonts, icons_dir):
    # fewer than 2 points takes the "Keine Daten" branch (no chart)
    _assert_cell(TemperatureChartModule().render(W, H, {"temperatures": [10.0]}, fonts, icons_dir))


@pytest.mark.parametrize("background", ["white", "black"])
def test_temperature_chart_with_spline(fonts, icons_dir, background):
    data = {"temperatures": [10.0, 10.4, 11.2, 12.0, 11.5, 10.8]}
    _assert_cell(TemperatureChartModule().render(W, H, data, fonts, icons_dir, background=background))


def test_temperature_chart_two_points_no_spline(fonts, icons_dir):
    # exactly 2 points plots without the k=2 spline branch
    _assert_cell(TemperatureChartModule().render(W, H, {"temperatures": [10.0, 12.0]}, fonts, icons_dir))


def test_forecast_empty(fonts, icons_dir):
    _assert_cell(ForecastModule().render(W, H, {}, fonts, icons_dir))


@pytest.mark.parametrize("background", ["white", "black"])
def test_forecast_with_days(fonts, icons_dir, background):
    day = {"date": "2035-06-01", "weekday": "Fri", "temp_max": "20",
           "temp_min": "8", "rain_prob": "40", "midday_icon": ")"}
    all_data = {"openweathermap": {"forecast": [day, day, day]}}
    params = {"forecast_source": "openweathermap"}
    img = ForecastModule().render(W, H, {}, fonts, icons_dir,
                                  background=background, params=params, all_data=all_data)
    _assert_cell(img)


def test_day_label_by_date():
    from datetime import date
    from src.modules.forecast import day_label

    today = date(2035, 6, 1)  # a Friday
    assert day_label("2035-06-01", "Fri", today) == "heute"
    assert day_label("2035-06-02", "Sat", today) == "morgen"
    assert day_label("2035-06-03", "Sun", today) == "So"


def test_day_label_late_evening_shift():
    # After the last of today's forecast slots has passed (~22:00 local), the
    # datasource's first day is already tomorrow: labels must follow the dates,
    # not the column positions (heute/morgen/<Sa> would be one day off).
    from datetime import date
    from src.modules.forecast import day_label

    today = date(2035, 5, 30)  # a Wednesday, forecast starts on Thursday
    assert day_label("2035-05-31", "Thu", today) == "morgen"
    assert day_label("2035-06-01", "Fri", today) == "Fr"
    assert day_label("2035-06-02", "Sat", today) == "Sa"


def test_forecast_single_day_no_separators(fonts, icons_dir):
    day = {"date": "2035-06-01", "weekday": "Fri", "temp_max": "20",
           "temp_min": "8", "rain_prob": "40", "midday_icon": ")"}
    all_data = {"openweathermap": {"forecast": [day]}}
    params = {"forecast_source": "openweathermap"}
    _assert_cell(ForecastModule().render(W, H, {}, fonts, icons_dir,
                                         params=params, all_data=all_data))
