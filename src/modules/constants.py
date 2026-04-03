# WeatherIcons-fixed.ttf glyph mapping for temperature trend arrows
TREND_MAP = {"stable": "2", "down": "1", "up": "0"}

# Reference cell dimensions from the original PHP layout (266x300 per cell)
BASE_CELL_WIDTH = 266
BASE_CELL_HEIGHT = 300


def cell_scale(width: int, height: int) -> tuple[float, float]:
    """Compute scale factors relative to the original PHP cell dimensions."""
    return width / BASE_CELL_WIDTH, height / BASE_CELL_HEIGHT
