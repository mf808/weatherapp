import os
from PIL import ImageFont


class FontRegistry:
    """Loads and caches TTF fonts from a directory.

    PHP GD renders TTF at 96 DPI, Pillow at 72 DPI.
    DPI_SCALE compensates so that font sizes match the original PHP output.
    """

    DPI_SCALE = 96 / 72  # ~1.333

    def __init__(self, fonts_dir: str):
        self._dir = fonts_dir
        self._cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}

    def get(self, name: str, size: int) -> ImageFont.FreeTypeFont:
        """Load font at the given size (already DPI-corrected by caller)."""
        key = (name, size)
        if key not in self._cache:
            path = os.path.join(self._dir, name)
            self._cache[key] = ImageFont.truetype(path, size)
        return self._cache[key]

    def scaled(self, name: str, php_size: float) -> ImageFont.FreeTypeFont:
        """Load font converting a PHP GD point size to Pillow equivalent."""
        return self.get(name, int(php_size * self.DPI_SCALE))

    @property
    def text_medium(self):
        return "Asap-Medium.ttf"

    @property
    def text_bold(self):
        return "Asap-Bold.ttf"

    @property
    def symbol(self):
        return "WeatherIcons-fixed.ttf"
