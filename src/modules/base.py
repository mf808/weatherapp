from abc import ABC, abstractmethod
from PIL import Image
from src.utils.fonts import FontRegistry


class Module(ABC):
    """Abstract base for all display modules."""

    @abstractmethod
    def render(
        self,
        width: int,
        height: int,
        data: dict,
        fonts: FontRegistry,
        icons_dir: str,
        background: str = "white",
        params: dict | None = None,
        all_data: dict | None = None,
    ) -> Image.Image:
        """Render this module into an image of the given dimensions."""
        ...
