from PIL import ImageFont

from src.utils.fonts import FontRegistry


def test_get_returns_freetype_font(fonts):
    f = fonts.get(fonts.text_medium, 20)
    assert isinstance(f, ImageFont.FreeTypeFont)


def test_scaled_applies_dpi_factor(fonts):
    """A PHP point size is multiplied by 96/72 and truncated to int."""
    php_size = 30
    f = fonts.scaled(fonts.text_medium, php_size)
    assert f.size == int(php_size * FontRegistry.DPI_SCALE)  # 40


def test_cache_returns_same_instance(fonts):
    a = fonts.get(fonts.text_bold, 24)
    b = fonts.get(fonts.text_bold, 24)
    assert a is b


def test_different_sizes_are_distinct(fonts):
    assert fonts.get(fonts.text_bold, 24) is not fonts.get(fonts.text_bold, 25)


def test_named_font_properties(fonts):
    assert fonts.text_medium.endswith(".ttf")
    assert fonts.text_bold.endswith(".ttf")
    assert fonts.symbol.endswith(".ttf")


def test_scaled_fractional_size_truncates(fonts):
    """cell_scale can produce fractional php sizes; truncation must stay > 0."""
    f = fonts.scaled(fonts.text_medium, 15 * 0.9)  # 13.5 -> *1.333 -> 17
    assert f.size == int(15 * 0.9 * FontRegistry.DPI_SCALE)
    assert f.size > 0
