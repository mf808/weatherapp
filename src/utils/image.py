import os
from PIL import Image


def load_battery_icon(icons_dir: str, status: str, size: int = 32, invert: bool = False) -> Image.Image:
    """Load a battery icon PNG, resize, and optionally invert for dark backgrounds."""
    path = os.path.join(icons_dir, f"battery-{status}-64x64.png")
    icon = Image.open(path).convert("RGBA")
    icon = icon.rotate(90, expand=True)
    icon = icon.resize((size, size), Image.LANCZOS)
    if invert:
        from PIL import ImageOps
        r, g, b, a = icon.split()
        rgb = Image.merge("RGB", (r, g, b))
        rgb = ImageOps.invert(rgb)
        icon = Image.merge("RGBA", (*rgb.split(), a))
    return icon


def apply_grayscale(image: Image.Image) -> Image.Image:
    """Convert image to grayscale."""
    return image.convert("L").convert("RGB")


def apply_rotation(image: Image.Image, degrees: int) -> Image.Image:
    """Rotate image by given degrees (counter-clockwise)."""
    if degrees:
        image = image.rotate(degrees, expand=True)
    return image
