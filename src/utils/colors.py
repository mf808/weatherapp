from dataclasses import dataclass


@dataclass(frozen=True)
class ColorScheme:
    bg: tuple[int, int, int]
    fg: tuple[int, int, int]
    grey: tuple[int, int, int]
    is_dark: bool


def color_scheme(background: str = "white") -> ColorScheme:
    """Derive a color scheme from the background setting."""
    is_dark = background == "black"
    return ColorScheme(
        bg=(0, 0, 0) if is_dark else (255, 255, 255),
        fg=(255, 255, 255) if is_dark else (0, 0, 0),
        grey=(200, 200, 200) if is_dark else (100, 100, 100),
        is_dark=is_dark,
    )
