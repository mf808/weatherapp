from PIL import Image, ImageDraw
from src.modules.base import Module
from src.modules.constants import TREND_MAP, cell_scale
from src.utils.colors import color_scheme
from src.utils.image import load_battery_icon


class OutdoorModule(Module):
    """Renders the outdoor/primary sensor panel: weather icon, temp, trend, pressure, humidity."""

    def render(self, width, height, data, fonts, icons_dir, background="white", params=None, all_data=None):
        colors = color_scheme(background)
        img = Image.new("RGB", (width, height), colors.bg)
        draw = ImageDraw.Draw(img)
        sx, sy = cell_scale(width, height)

        # Module name
        font_name = fonts.scaled("Asap-SemiBold.ttf", 20 * sy)
        draw.text((int(15 * sx), int(30 * sy)), data.get("name", "Outdoor"),
                  font=font_name, fill=colors.fg, anchor="ls")

        # Battery icon
        bat_size = int(32 * min(sx, sy))
        bat_icon = load_battery_icon(icons_dir, data.get("battery_status", "full"), bat_size, invert=colors.is_dark)
        img.paste(bat_icon, (int(230 * sx), int(0 * sy)), bat_icon)

        # Weather icon from openweathermap
        weather_glyph = "b"
        if params and all_data:
            weather_source = params.get("weather_source")
            weather_key = params.get("weather_key")
            if weather_source and weather_key:
                weather_data = all_data.get(weather_source, {}).get(weather_key, {})
                weather_glyph = weather_data.get("icon_glyph", "b")

        font_icon = fonts.scaled(fonts.symbol, 60 * sy)
        draw.text((int(80 * sx), int(130 * sy)), weather_glyph,
                  font=font_icon, fill=colors.fg, anchor="ls")

        # Temperature — "--" (not "0.0") when data is entirely missing (e.g. a
        # datasource fetch failure with no last-known-good cache available either),
        # so a real 0.0°C reading is never confused with "we have no reading at all".
        temp_str = data.get("temp", "--")
        font_temp = fonts.scaled(fonts.text_bold, 45 * sy)
        font_deg = fonts.scaled(fonts.symbol, 45 * sy)
        font_trend = fonts.scaled(fonts.symbol, 20 * sy)

        temp_x = int(80 * sx)
        if len(temp_str) > 4:
            temp_x = int((80 - 22) * sx)

        draw.text((temp_x, int(210 * sy)), temp_str,
                  font=font_temp, fill=colors.fg, anchor="ls")

        temp_bbox = font_temp.getbbox(temp_str)
        temp_w = temp_bbox[2] - temp_bbox[0]
        deg_x = temp_x + temp_w + int(5 * sx)
        draw.text((deg_x, int(210 * sy)), "c",
                  font=font_deg, fill=colors.fg, anchor="ls")

        trend = TREND_MAP.get(data.get("temp_trend", "stable"), "2")
        deg_bbox = font_deg.getbbox("c")
        trend_x = deg_x + (deg_bbox[2] - deg_bbox[0]) + int(2 * sx)
        draw.text((trend_x, int(210 * sy)), trend,
                  font=font_trend, fill=colors.fg, anchor="ls")

        # Pressure
        pressure = None
        if all_data:
            for source_data in all_data.values():
                if isinstance(source_data, dict):
                    for v in source_data.values():
                        if isinstance(v, dict) and "pressure" in v:
                            pressure = v["pressure"]
                            break

        if pressure is not None:
            press_int = int(pressure)
            press_dec = f"{pressure - press_int:.1f}".lstrip("0")
            font_press = fonts.scaled(fonts.text_bold, 30 * sy)
            font_press_dec = fonts.scaled(fonts.text_bold, 20 * sy)
            font_label = fonts.scaled(fonts.text_medium, 15 * sy)

            press_str = f" {press_int}" if press_int < 1000 else str(press_int)
            draw.text((int(12 * sx), int(255 * sy)), press_str,
                      font=font_press, fill=colors.fg, anchor="ls")
            press_bbox = font_press.getbbox(press_str)
            press_w = press_bbox[2] - press_bbox[0]
            draw.text((int(12 * sx) + press_w + int(5 * sx), int(255 * sy)),
                       press_dec, font=font_press_dec, fill=colors.fg, anchor="ls")
            draw.text((int(13 * sx), int(275 * sy)), "mBar Druck",
                      font=font_label, fill=colors.grey, anchor="ls")

        # Humidity
        humidity = data.get("humidity", "")
        if humidity != "":
            font_hum = fonts.scaled(fonts.text_bold, 30 * sy)
            font_pct = fonts.scaled(fonts.text_bold, 20 * sy)
            font_label = fonts.scaled(fonts.text_medium, 15 * sy)

            draw.text((int(166 * sx), int(255 * sy)), str(humidity),
                      font=font_hum, fill=colors.fg, anchor="ls")
            hum_bbox = font_hum.getbbox(str(humidity))
            hum_w = hum_bbox[2] - hum_bbox[0]
            draw.text((int(166 * sx) + hum_w + int(2 * sx), int(255 * sy)),
                       "%", font=font_pct, fill=colors.fg, anchor="ls")
            draw.text((int(149 * sx), int(275 * sy)), "Feuchtigkeit",
                      font=font_label, fill=colors.grey, anchor="ls")

        return img
