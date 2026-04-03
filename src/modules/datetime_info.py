from datetime import datetime

from PIL import Image, ImageDraw
from src.modules.base import Module
from src.modules.constants import cell_scale
from src.utils.colors import color_scheme


class DateTimeModule(Module):
    """Renders current date and time."""

    def render(self, width, height, data, fonts, icons_dir, background="white", params=None, all_data=None):
        colors = color_scheme(background)
        img = Image.new("RGB", (width, height), colors.bg)
        draw = ImageDraw.Draw(img)
        sx, sy = cell_scale(width, height)

        now = datetime.now()
        font_label = fonts.scaled(fonts.text_medium, 20 * sy)
        font_date = fonts.scaled(fonts.text_medium, 18 * sy)

        draw.text((int(80 * sx), int(30 * sy)), "Messung vom:",
                  font=font_label, fill=colors.fg, anchor="ls")
        draw.text((int(105 * sx), int(70 * sy)), now.strftime("%d.%m.%Y"),
                  font=font_date, fill=colors.fg, anchor="ls")
        draw.text((int(135 * sx), int(100 * sy)), now.strftime("%H:%M"),
                  font=font_date, fill=colors.fg, anchor="ls")

        return img
