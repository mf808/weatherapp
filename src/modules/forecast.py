from datetime import datetime

from PIL import Image, ImageDraw
from src.modules.base import Module
from src.modules.constants import cell_scale
from src.utils.colors import color_scheme


GERMAN_DAY_LABELS = {
    "Mon": "Mo", "Tue": "Di", "Wed": "Mi",
    "Thu": "Do", "Fri": "Fr", "Sat": "Sa", "Sun": "So",
}


class ForecastModule(Module):
    """Renders a 3-day weather forecast in columns with separators."""

    def render(self, width, height, data, fonts, icons_dir, background="white", params=None, all_data=None):
        colors = color_scheme(background)
        sep_color = (180, 180, 180) if not colors.is_dark else (80, 80, 80)

        img = Image.new("RGB", (width, height), colors.bg)
        draw = ImageDraw.Draw(img)
        sx, sy = cell_scale(width, height)

        # Get forecast days
        forecast_days = []
        if params and all_data:
            source = params.get("forecast_source", "openweathermap")
            forecast_days = all_data.get(source, {}).get("forecast", [])

        if not forecast_days:
            font_empty = fonts.scaled(fonts.text_medium, 15 * sy)
            draw.text((int(15 * sx), int(150 * sy)), "Keine Vorhersage",
                      font=font_empty, fill=colors.grey, anchor="ls")
            return img

        # Fonts
        font_label = fonts.scaled("Asap-SemiBold.ttf", 16 * sy)
        font_date = fonts.scaled(fonts.text_medium, 12 * sy)
        font_temp_max = fonts.scaled(fonts.text_bold, 26 * sy)
        font_temp_min = fonts.scaled(fonts.text_medium, 16 * sy)
        font_icon = fonts.scaled(fonts.symbol, 30 * sy)
        font_deg_max = fonts.scaled(fonts.symbol, 26 * sy)
        font_deg_min = fonts.scaled(fonts.symbol, 16 * sy)
        font_rain = fonts.scaled(fonts.text_medium, 12 * sy)

        num_cols = min(len(forecast_days), 3)
        col_width = width / num_cols

        # Column separators
        for i in range(1, num_cols):
            sep_x = int(i * col_width)
            draw.line([(sep_x, int(10 * sy)), (sep_x, int(285 * sy))],
                      fill=sep_color, width=1)

        for i, day in enumerate(forecast_days[:3]):
            cx = int(i * col_width + col_width / 2)

            if i == 0:
                label = "heute"
            elif i == 1:
                label = "morgen"
            else:
                label = GERMAN_DAY_LABELS.get(day["weekday"], day["weekday"])

            dt = datetime.strptime(day["date"], "%Y-%m-%d")
            date_str = dt.strftime("%d.%m.")

            draw.text((cx, int(25 * sy)), label,
                      font=font_label, fill=colors.fg, anchor="ms")
            draw.text((cx, int(48 * sy)), date_str,
                      font=font_date, fill=colors.grey, anchor="ms")

            # Max temp
            max_str = day["temp_max"]
            max_bbox = font_temp_max.getbbox(max_str)
            max_w = max_bbox[2] - max_bbox[0]
            deg_bbox = font_deg_max.getbbox("c")
            deg_w = deg_bbox[2] - deg_bbox[0]
            total_w = max_w + deg_w
            max_x = cx - total_w // 2
            draw.text((max_x, int(90 * sy)), max_str,
                      font=font_temp_max, fill=colors.fg, anchor="ls")
            draw.text((max_x + max_w, int(90 * sy)), "c",
                      font=font_deg_max, fill=colors.fg, anchor="ls")

            # Min temp
            min_str = day["temp_min"]
            min_bbox = font_temp_min.getbbox(min_str)
            min_w = min_bbox[2] - min_bbox[0]
            deg_min_bbox = font_deg_min.getbbox("c")
            deg_min_w = deg_min_bbox[2] - deg_min_bbox[0]
            total_min_w = min_w + deg_min_w
            min_x = cx - total_min_w // 2
            draw.text((min_x, int(120 * sy)), min_str,
                      font=font_temp_min, fill=colors.grey, anchor="ls")
            draw.text((min_x + min_w, int(120 * sy)), "c",
                      font=font_deg_min, fill=colors.grey, anchor="ls")

            # Weather icon
            icon_glyph = day["midday_icon"]
            icon_bbox = font_icon.getbbox(icon_glyph)
            icon_w = icon_bbox[2] - icon_bbox[0]
            draw.text((cx - icon_w // 2, int(190 * sy)), icon_glyph,
                      font=font_icon, fill=colors.fg, anchor="ls")

            # Rain probability
            font_umbrella = fonts.scaled(fonts.symbol, 14 * sy)
            umbrella_glyph = "6"
            umbrella_bbox = font_umbrella.getbbox(umbrella_glyph)
            umbrella_w = umbrella_bbox[2] - umbrella_bbox[0]
            rain_text = f"{day['rain_prob']}%"
            rain_bbox = font_rain.getbbox(rain_text)
            rain_w = rain_bbox[2] - rain_bbox[0]
            total_rain_w = umbrella_w + int(4 * sx) + rain_w
            rain_x = cx - total_rain_w // 2
            draw.text((rain_x, int(250 * sy)), umbrella_glyph,
                      font=font_umbrella, fill=colors.grey, anchor="ls")
            draw.text((rain_x + umbrella_w + int(4 * sx), int(250 * sy)), rain_text,
                      font=font_rain, fill=colors.grey, anchor="ls")

        return img
