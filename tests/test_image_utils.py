from PIL import Image

from src.utils.image import apply_grayscale, apply_rotation, load_battery_icon


def test_grayscale_produces_mode_L():
    img = Image.new("RGB", (10, 10), (128, 64, 32))
    assert apply_grayscale(img).mode == "L"


def test_rotation_90_swaps_dimensions():
    img = Image.new("RGB", (800, 600))
    rotated = apply_rotation(img, 90)
    assert rotated.size == (600, 800)


def test_rotation_zero_is_noop():
    img = Image.new("RGB", (800, 600))
    out = apply_rotation(img, 0)
    assert out.size == (800, 600)


def test_rotation_180_keeps_dimensions():
    img = Image.new("RGB", (800, 600))
    assert apply_rotation(img, 180).size == (800, 600)


# ── Battery icon loading (reads real PNGs from icons/) ──────────

def test_load_battery_icon_size_and_mode(icons_dir):
    icon = load_battery_icon(icons_dir, "full", size=48)
    assert icon.size == (48, 48)
    assert icon.mode == "RGBA"


def test_load_battery_icon_all_statuses(icons_dir):
    for status in ("full", "half", "low", "empty", "charging"):
        icon = load_battery_icon(icons_dir, status, size=32)
        assert icon.size == (32, 32)


def test_load_battery_icon_invert_changes_pixels(icons_dir):
    """Inversion for dark backgrounds must actually alter the RGB channels."""
    normal = load_battery_icon(icons_dir, "full", size=32, invert=False)
    inverted = load_battery_icon(icons_dir, "full", size=32, invert=True)
    assert normal.tobytes() != inverted.tobytes()
    assert inverted.mode == "RGBA"


def test_load_battery_icon_missing_status_raises(icons_dir):
    import pytest
    with pytest.raises(FileNotFoundError):
        load_battery_icon(icons_dir, "does-not-exist")
