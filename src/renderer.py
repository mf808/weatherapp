from datetime import datetime

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
            x_offset += cell_width

        y_offset += row_height

    # Timestamp watermark — bottom center of middle lower quadrant
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    wm_font = fonts.scaled(fonts.text_medium, 10)
    wm_bbox = wm_font.getbbox(now_str)
    wm_w = wm_bbox[2] - wm_bbox[0]
    # Middle lower cell: x from width*0.33 to width*0.67, y at bottom
    mid_center_x = int(width * 0.5)
    wm_x = mid_center_x - wm_w // 2
    wm_y = height - wm_bbox[3] + wm_bbox[1] - 4
    draw = ImageDraw.Draw(img)
    draw.text((wm_x, wm_y), now_str, font=wm_font, fill=(100, 100, 100))

    # Apply device-specific post-processing
    if device_cfg.get("rotation"):
        img = apply_rotation(img, device_cfg["rotation"])
    if device_cfg.get("grayscale"):
        img = apply_grayscale(img)

    return img
