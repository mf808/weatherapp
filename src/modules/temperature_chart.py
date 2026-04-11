import io
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import make_interp_spline
from PIL import Image, ImageDraw

from src.modules.base import Module
from src.modules.constants import cell_scale
from src.utils.colors import color_scheme


class TemperatureChartModule(Module):
    """Renders a 6-hour temperature trend chart using matplotlib."""

    def render(self, width, height, data, fonts, icons_dir, background="white", params=None, all_data=None):
        colors = color_scheme(background)
        img = Image.new("RGB", (width, height), colors.bg)
        sx, sy = cell_scale(width, height)

        # Title
        draw = ImageDraw.Draw(img)
        font_title = fonts.scaled(fonts.text_medium, 20 * sy)
        draw.text((int(15 * sx), int(30 * sy)), "Temperaturverlauf 6h",
                  font=font_title, fill=colors.fg, anchor="ls")

        temps = data.get("temperatures", [])
        if len(temps) < 2:
            font = fonts.scaled(fonts.text_medium, 15 * sy)
            draw.text((int(15 * sx), int(height // 2)), "Keine Daten",
                      font=font, fill=colors.fg, anchor="ls")
            return img

        # Chart area
        chart_y = int(50 * sy)
        chart_width = width
        chart_height = height - chart_y

        font_path = os.path.join(fonts._dir, fonts.text_medium)
        line_color = "black" if not colors.is_dark else "white"
        bg_str = "black" if colors.is_dark else "white"

        # Create matplotlib figure
        dpi = 100
        fig, ax = plt.subplots(1, 1, figsize=(chart_width / dpi, chart_height / dpi), dpi=dpi)
        fig.patch.set_facecolor(bg_str)
        ax.set_facecolor(bg_str)

        x = np.arange(len(temps))

        # Light B-spline smoothing (k=2 quadratic)
        if len(temps) >= 3:
            spl = make_interp_spline(x, temps, k=2)
            x_smooth = np.linspace(0, len(temps) - 1, len(temps) * 4)
            y_smooth = spl(x_smooth)
            ax.plot(x_smooth, y_smooth, color="navy", linewidth=3)
        else:
            ax.plot(x, temps, color="navy", linewidth=3)

        # X-axis: hour labels at whole-hour positions
        now_hour = datetime.now(tz=ZoneInfo(os.environ.get("TZ", "Europe/Berlin"))).hour
        hours_back = len(temps) / 2
        tick_positions = list(range(0, len(temps), 2))
        tick_labels = [str(int(now_hour - hours_back + 1 + i)) for i in range(len(tick_positions))]
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels)

        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1f}\u00b0"))

        from matplotlib.font_manager import FontProperties
        font_prop = FontProperties(fname=font_path, size=int(11 * fonts.DPI_SCALE * min(sx, sy)))

        ax.tick_params(colors=line_color)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(font_prop)
            label.set_color(line_color)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.yaxis.grid(True, color=line_color, linewidth=0.5, alpha=0.3)
        ax.tick_params(axis="both", which="both", length=0)

        if len(temps) > 0:
            ymin, ymax = min(temps), max(temps)
            margin = max((ymax - ymin) * 0.5, 0.5)
            ax.set_ylim(ymin - margin, ymax + margin)

        fig.tight_layout(pad=0.3)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        chart_img = Image.open(buf).convert("RGB").resize((chart_width, chart_height), Image.LANCZOS)
        img.paste(chart_img, (0, chart_y))
        buf.close()

        return img
