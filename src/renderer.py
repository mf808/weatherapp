import os
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw

from src.modules.base import Module
from src.modules.outdoor import OutdoorModule
from src.modules.room_climate import RoomClimateModule
from src.modules.temperature_chart import TemperatureChartModule
from src.modules.datetime_info import DateTimeModule
from src.modules.forecast import ForecastModule
from src.utils.fonts import FontRegistry
from src.utils.image import apply_grayscale, apply_rotation


MODULE_REGISTRY: dict[str, type[Module]] = {
    "outdoor": OutdoorModule,
    "room_climate": RoomClimateModule,
    "temperature_chart": TemperatureChartModule,
    "datetime_info": DateTimeModule,
    "forecast": ForecastModule,
}


def render(config: dict, all_data: dict, fonts: FontRegistry, icons_dir: str) -> Image.Image:
    """Render the full display image based on config and fetched data."""
    device_cfg = config["devices"][config["device"]]
    width = device_cfg["width"]
    height = device_cfg["height"]

    img = Image.new("RGB", (width, height), (255, 255, 255))

    layout = config["layout"]
    y_offset = 0
    chart_cell_bounds = None  # (x, y, width, height) of the temperature_chart cell, if present

    for row in layout["rows"]:
        row_height = int(height * row["height"])
        row_bg = row.get("background", "white")
        x_offset = 0

        for cell in row["cells"]:
            cell_width = int(width * cell["width"])
            module_name = cell["module"]

            # Get data for this cell
            source_name = cell.get("source")
            source_key = cell.get("source_key")
            cell_data = {}
            if source_name and source_key:
                cell_data = all_data.get(source_name, {}).get(source_key, {})

            # Instantiate and render module
            module_cls = MODULE_REGISTRY.get(module_name)
            if module_cls is None:
                print(f"Warning: Unknown module '{module_name}', skipping")
                x_offset += cell_width
                continue

            module = module_cls()
            cell_img = module.render(
                width=cell_width,
                height=row_height,
                data=cell_data,
                fonts=fonts,
                icons_dir=icons_dir,
                background=row_bg,
                params=cell.get("params"),
                all_data=all_data,
            )

            img.paste(cell_img, (x_offset, y_offset))
            if module_name == "temperature_chart":
                chart_cell_bounds = (x_offset, y_offset, cell_width, row_height)
            x_offset += cell_width

        y_offset += row_height

    # Timestamp watermark — bottom center of middle lower quadrant
    now_str = datetime.now(tz=ZoneInfo(os.environ.get("TZ", "Europe/Berlin"))).strftime("%d.%m.%Y %H:%M")
    wm_font = fonts.scaled(fonts.text_medium, 10)
    wm_bbox = wm_font.getbbox(now_str)
    wm_w = wm_bbox[2] - wm_bbox[0]
    # Middle lower cell: x from width*0.33 to width*0.67, y at bottom
    mid_center_x = int(width * 0.5)
    wm_x = mid_center_x - wm_w // 2
    wm_y = height - wm_bbox[3] + wm_bbox[1] - 4
    draw = ImageDraw.Draw(img)
    draw.text((wm_x, wm_y), now_str, font=wm_font, fill=(180, 180, 180))

    # Stale-data banner — a solid black bar with bold white text, pinned to the
    # bottom edge of the temperature_chart cell (drawn last, on top of that cell's
    # already-pasted content, so it never spills into the row below and overlaps
    # the room panels). Only drawn when a datasource fell back to a cached
    # last-known-good reading (see NetatmoSource._fallback()) instead of a fresh one.
    stale_meta = (all_data or {}).get("netatmo", {}).get("_stale")
    if stale_meta and chart_cell_bounds:
        cell_x, cell_y, cell_w, cell_h = chart_cell_bounds
        as_of = stale_meta.get("as_of")
        try:
            as_of_str = datetime.fromtimestamp(as_of, tz=ZoneInfo(os.environ.get("TZ", "Europe/Berlin"))).strftime("%H:%M")
        except (TypeError, ValueError, OSError):
            as_of_str = "?"
        stale_text = f"Stand {as_of_str}"
        stale_font = fonts.scaled(fonts.text_bold, 16)
        stale_bbox = stale_font.getbbox(stale_text)
        stale_w = stale_bbox[2] - stale_bbox[0]
        stale_h = stale_bbox[3] - stale_bbox[1]
        pad_x, pad_y = 10, 6
        # The bar always widens to at least fit the text (+ padding), even if that's
        # wider than the chart cell - centered on the cell either way. Without this,
        # text wider than cell_w would start left of the bar and render as invisible
        # white-on-white over the neighboring cell (this happened in practice).
        bar_w = max(cell_w, stale_w + pad_x * 2)
        bar_h = stale_h + pad_y * 2
        bar_x0 = cell_x + (cell_w - bar_w) // 2
        bar_top = cell_y + cell_h - bar_h
        draw.rectangle([bar_x0, bar_top, bar_x0 + bar_w, cell_y + cell_h], fill=(0, 0, 0))
        text_x = bar_x0 + (bar_w - stale_w) // 2
        text_y = bar_top + pad_y - stale_bbox[1]
        draw.text((text_x, text_y), stale_text, font=stale_font, fill=(255, 255, 255))

    # Apply device-specific post-processing
    if device_cfg.get("rotation"):
        img = apply_rotation(img, device_cfg["rotation"])
    if device_cfg.get("grayscale"):
        img = apply_grayscale(img)

    return img
