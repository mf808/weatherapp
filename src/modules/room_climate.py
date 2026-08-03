from PIL import Image, ImageDraw
from src.modules.base import Module
from src.modules.constants import TREND_MAP, cell_scale
from src.utils.colors import color_scheme
from src.utils.image import load_battery_icon


class RoomClimateModule(Module):
    """Renders an indoor sensor card: temp, trend, air quality status, CO2, humidity."""

    def render(self, width, height, data, fonts, icons_dir, background="white", params=None, all_data=None):
        colors = color_scheme(background)
        img = Image.new("RGB", (width, height), colors.bg)
        draw = ImageDraw.Draw(img)
        sx, sy = cell_scale(width, height)

        # Module name
        font_name = fonts.scaled(fonts.text_medium, 20 * sy)
        draw.text((int(15 * sx), int(30 * sy)), data.get("name", ""),
                  font=font_name, fill=colors.fg, anchor="ls")

        # Battery icon
        bat_size = int(32 * min(sx, sy))
        bat_icon = load_battery_icon(icons_dir, data.get("battery_status", "full"), bat_size, invert=colors.is_dark)
        img.paste(bat_icon, (int(230 * sx), 0), bat_icon)

        # Temperature — "--" (not "0.0") when data is entirely missing, so a real
        # 0.0°C reading is never confused with "we have no reading at all".
        temp_str = data.get("temp", "--")
        font_temp = fonts.scaled(fonts.text_bold, 45 * sy)
        font_deg = fonts.scaled(fonts.symbol, 45 * sy)
        font_trend = fonts.scaled(fonts.symbol, 20 * sy)

        draw.text((int(80 * sx), int(100 * sy)), temp_str,
                  font=font_temp, fill=colors.fg, anchor="ls")

        temp_bbox = font_temp.getbbox(temp_str)
        temp_w = temp_bbox[2] - temp_bbox[0]
        deg_x = int(80 * sx) + temp_w + int(5 * sx)
        draw.text((deg_x, int(100 * sy)), "c",
                  font=font_deg, fill=colors.fg, anchor="ls")

        trend = TREND_MAP.get(data.get("temp_trend", "stable"), "2")
        deg_bbox = font_deg.getbbox("c")
        trend_x = deg_x + (deg_bbox[2] - deg_bbox[0]) + int(2 * sx)
        draw.text((trend_x, int(100 * sy)), trend,
                  font=font_trend, fill=colors.fg, anchor="ls")

        # Air quality
        co2 = data.get("co2", 0)
        humidity = data.get("humidity", 0)
        try:
            co2_val = int(co2) if co2 != "" else 0
        except (ValueError, TypeError):
            co2_val = 0
        try:
            hum_val = int(humidity) if humidity != "" else 0
        except (ValueError, TypeError):
            hum_val = 0

        font_status = fonts.scaled(fonts.text_bold, 40 * sy)
        font_label = fonts.scaled(fonts.text_medium, 15 * sy)

        if not data:
            # No reading at all for this room (missing cell data) - "Gut" would
            # falsely look like a real "good air quality" reading, not an absence.
            status_text = "--"
            status_x = int(90 * sx)
        elif co2_val > 1200 or hum_val > 60:
            status_text = "L\u00fcften"
            status_x = int(57 * sx)
        else:
            status_text = "Gut"
            status_x = int(90 * sx)

        draw.text((status_x, int(165 * sy)), status_text,
                  font=font_status, fill=colors.fg, anchor="ls")
        draw.text((int(84 * sx), int(185 * sy)), "Raumklima",
                  font=font_label, fill=colors.grey, anchor="ls")

        # CO2
        font_value = fonts.scaled(fonts.text_bold, 30 * sy)
        font_unit = fonts.scaled(fonts.text_medium, 15 * sy)

        co2_str = str(co2_val) if co2_val else ""
        if co2_str and len(co2_str) < 4:
            co2_str = " " + co2_str
        if co2_str:
            draw.text((int(25 * sx), int(250 * sy)), co2_str,
                      font=font_value, fill=colors.fg, anchor="ls")
            draw.text((int(28 * sx), int(270 * sy)), "ppm Co2",
                      font=font_unit, fill=colors.grey, anchor="ls")

        # Humidity
        if hum_val:
            font_pct = fonts.scaled(fonts.text_bold, 20 * sy)
            draw.text((int(166 * sx), int(250 * sy)), str(hum_val),
                      font=font_value, fill=colors.fg, anchor="ls")
            hum_bbox = font_value.getbbox(str(hum_val))
            hum_w = hum_bbox[2] - hum_bbox[0]
            draw.text((int(166 * sx) + hum_w + int(2 * sx), int(250 * sy)),
                       "%", font=font_pct, fill=colors.fg, anchor="ls")
            draw.text((int(149 * sx), int(270 * sy)), "Feuchtigkeit",
                      font=font_unit, fill=colors.grey, anchor="ls")

        return img
