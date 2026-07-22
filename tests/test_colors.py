from src.utils.colors import color_scheme


def test_white_scheme_is_light():
    c = color_scheme("white")
    assert c.is_dark is False
    assert c.bg == (255, 255, 255)
    assert c.fg == (0, 0, 0)


def test_black_scheme_is_dark():
    c = color_scheme("black")
    assert c.is_dark is True
    assert c.bg == (0, 0, 0)
    assert c.fg == (255, 255, 255)


def test_default_is_light():
    assert color_scheme().is_dark is False


def test_unknown_background_defaults_to_light():
    """Only the literal 'black' is dark; anything else falls back to light."""
    assert color_scheme("chartreuse").is_dark is False


def test_scheme_is_frozen():
    import dataclasses
    import pytest

    c = color_scheme("white")
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.bg = (1, 2, 3)
