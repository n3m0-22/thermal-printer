"""pil compatibility module for graceful imagetk fallback
handles systems where pil is installed without tk bindings like fedora
"""

from typing import Optional, Any
import warnings

# always available PIL components
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# attempt to import imagetk with graceful fallback
_IMAGETK_AVAILABLE = False

try:
    from PIL import ImageTk as _ImageTk
    _IMAGETK_AVAILABLE = True
except ImportError:
    _ImageTk = None
    warnings.warn(
        "PIL.ImageTk not available. Image preview features will be disabled. "
        "On Fedora/RHEL, install: sudo dnf install python3-pillow-tk",
        ImportWarning
    )


def is_imagetk_available() -> bool:
    return _IMAGETK_AVAILABLE


class DummyPhotoImage:
    """placeholder for imagetk photoimage when imagetk not available allows code to run without crashing"""

    def __init__(self, image: Optional[Image.Image] = None, **kwargs):
        self._image = image
        self._width = image.width if image else 1
        self._height = image.height if image else 1

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height

    def __bool__(self) -> bool:
        return False


# export the appropriate photoimage class
if _IMAGETK_AVAILABLE:
    PhotoImage = _ImageTk.PhotoImage
    BitmapImage = _ImageTk.BitmapImage
else:
    PhotoImage = DummyPhotoImage
    BitmapImage = DummyPhotoImage


def create_photo_image(image: Image.Image) -> Any:
    """create photoimage from pil image returns none if imagetk not available"""
    if not _IMAGETK_AVAILABLE:
        return None
    return _ImageTk.PhotoImage(image)


# reexport common pil components for convenience
__all__ = [
    'Image',
    'ImageDraw',
    'ImageFont',
    'ImageEnhance',
    'PhotoImage',
    'BitmapImage',
    'is_imagetk_available',
    'create_photo_image',
]
