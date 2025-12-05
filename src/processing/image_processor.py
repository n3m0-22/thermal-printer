"""Image processing for thermal printing.

This module converts color/grayscale images to 1-bit black and white format
suitable for thermal printing. It handles resizing, brightness/contrast
adjustment, rotation, and dithering using various algorithms.

The thermal printer protocol uses inverted pixels (1 = ink, 0 = no ink), which
is opposite of normal image conventions (0 = black). Images are inverted during
process() for the printer, then re-inverted in get_full_preview() so users see
a correct visual representation. The user's "invert" option happens before
this protocol conversion so it affects the visual appearance as expected.

Error diffusion dithering algorithms are inherently sequential because each
pixel's output depends on accumulated error from previously processed pixels.
The _error_diffusion_dither method uses pre-computed inverse divisors and
local variable caching to minimize Python interpreter overhead within the
required pixel-by-pixel loop.
"""

from typing import Tuple, List
import numpy as np
from PIL import Image, ImageOps, ImageEnhance

from ..config.defaults import (
    DEFAULT_BRIGHTNESS,
    DEFAULT_CONTRAST,
    DEFAULT_DITHER_MODE,
    DEFAULT_ROTATION,
)
from ..core.protocol import PrinterProtocol
from ..core.exceptions import InvalidImageError


class ImageProcessor:

    def __init__(
        self,
        printer_width: int = PrinterProtocol.PRINTER_WIDTH,
        brightness: float = DEFAULT_BRIGHTNESS,
        contrast: float = DEFAULT_CONTRAST,
        dither_mode: str = DEFAULT_DITHER_MODE,
        rotation: int = DEFAULT_ROTATION,
        invert: bool = False,
        auto_resize: bool = True,
    ):
        self.printer_width = printer_width
        self.brightness = brightness
        self.contrast = contrast
        self.dither_mode = dither_mode
        self.rotation = rotation
        self.invert = invert
        self.auto_resize = auto_resize

    def process(self, image: Image.Image) -> Image.Image:

        if image is None:
            raise InvalidImageError("No image provided")

        img = image.copy()

        if self.rotation != 0:
            img = self._rotate(img)

        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')

        if self.auto_resize:
            img = self._resize(img)

        if self.brightness != 1.0:
            img = self._adjust_brightness(img)
        if self.contrast != 1.0:
            img = self._adjust_contrast(img)

        if self.invert:
            img = ImageOps.invert(img.convert('RGB'))

        if img.mode != 'L':
            img = img.convert('L')

        img = self._apply_dithering(img)
        img = self._pad_width(img)

        # invert for printer where black pixels equal 1
        img = ImageOps.invert(img.convert('L'))
        img = img.convert('1')

        return img

    def _rotate(self, img: Image.Image) -> Image.Image:
        if self.rotation == 90:
            return img.transpose(Image.Transpose.ROTATE_90)
        elif self.rotation == 180:
            return img.transpose(Image.Transpose.ROTATE_180)
        elif self.rotation == 270:
            return img.transpose(Image.Transpose.ROTATE_270)
        return img

    def _resize(self, img: Image.Image) -> Image.Image:
        if img.width == self.printer_width:
            return img

        if img.width > self.printer_width:
            scale = self.printer_width / img.width
            new_height = int(img.height * scale)
            return img.resize(
                (self.printer_width, new_height),
                Image.Resampling.LANCZOS
            )
        else:
            padded = Image.new(img.mode, (self.printer_width, img.height), 'white')
            x_offset = (self.printer_width - img.width) // 2
            padded.paste(img, (x_offset, 0))
            return padded

    def _adjust_brightness(self, img: Image.Image) -> Image.Image:
        enhancer = ImageEnhance.Brightness(img)
        return enhancer.enhance(self.brightness)

    def _adjust_contrast(self, img: Image.Image) -> Image.Image:
        enhancer = ImageEnhance.Contrast(img)
        return enhancer.enhance(self.contrast)

    def _apply_dithering(self, img: Image.Image) -> Image.Image:
        if img.mode != 'L':
            img = img.convert('L')

        mode = self.dither_mode.lower()

        if mode == 'none':
            return img.point(lambda x: 255 if x > 127 else 0, '1')
        elif mode == 'floyd-steinberg':
            return img.convert('1')
        elif mode == 'ordered':
            return self._ordered_dither(img)
        elif mode == 'atkinson':
            return self._atkinson_dither(img)
        elif mode == 'burkes':
            return self._burkes_dither(img)
        elif mode == 'sierra':
            return self._sierra_dither(img)
        elif mode == 'stucki':
            return self._stucki_dither(img)
        else:
            return img.convert('1')

    def _ordered_dither(self, img: Image.Image) -> Image.Image:
        # 4x4 bayer matrix for ordered dithering
        bayer_matrix = np.array([
            [0, 8, 2, 10],
            [12, 4, 14, 6],
            [3, 11, 1, 9],
            [15, 7, 13, 5]
        ]) * 16

        pixels = np.array(img, dtype=np.float32)
        height, width = pixels.shape

        threshold = np.tile(bayer_matrix, (height // 4 + 1, width // 4 + 1))
        threshold = threshold[:height, :width]

        result = (pixels > threshold).astype(np.uint8) * 255
        return Image.fromarray(result, mode='L').convert('1')

    def _error_diffusion_dither(
        self,
        img: Image.Image,
        diffusion_matrix: List[Tuple[int, int, int]],
        divisor: int
    ) -> Image.Image:

        pixels = np.ascontiguousarray(img, dtype=np.float32)
        height, width = pixels.shape

        same_row, next_row, next_next_row = self._prepare_diffusion_weights(
            diffusion_matrix, divisor
        )

        self._apply_error_diffusion(
            pixels, width, height, same_row, next_row, next_next_row
        )

        result = (pixels > 127).astype(np.uint8) * 255
        return Image.fromarray(result, mode='L').convert('1')

    def _prepare_diffusion_weights(
        self,
        diffusion_matrix: List[Tuple[int, int, int]],
        divisor: int
    ) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]], List[Tuple[int, float]]]:
        # separate diffusion weights by row offset for optimized propagation
        weights = [(dx, dy, weight / divisor) for dx, dy, weight in diffusion_matrix]

        same_row = [(dx, w) for dx, dy, w in weights if dy == 0]
        next_row = [(dx, w) for dx, dy, w in weights if dy == 1]
        next_next_row = [(dx, w) for dx, dy, w in weights if dy == 2]

        return same_row, next_row, next_next_row

    def _apply_error_diffusion(
        self,
        pixels: np.ndarray,
        width: int,
        height: int,
        same_row: List[Tuple[int, float]],
        next_row: List[Tuple[int, float]],
        next_next_row: List[Tuple[int, float]]
    ) -> None:
        # precompute bounds to avoid repeated calculations in tight loop
        width_minus_1 = width - 1
        height_minus_1 = height - 1

        for y in range(height):
            row = pixels[y]
            has_next_row = y < height_minus_1
            has_next_next_row = y < height_minus_1 - 1

            for x in range(width):
                old_val = row[x]
                new_val = 255.0 if old_val > 127.0 else 0.0
                row[x] = new_val
                err = old_val - new_val

                # skip error diffusion if pixel already at target value
                if err == 0.0:
                    continue

                self._propagate_error_same_row(row, x, err, same_row, width_minus_1)

                if has_next_row:
                    self._propagate_error_next_row(
                        pixels[y + 1], x, err, next_row, width_minus_1
                    )

                if has_next_next_row and next_next_row:
                    self._propagate_error_next_row(
                        pixels[y + 2], x, err, next_next_row, width_minus_1
                    )

    def _propagate_error_same_row(
        self,
        row: np.ndarray,
        x: int,
        err: float,
        weights: List[Tuple[int, float]],
        width_minus_1: int
    ) -> None:
        for dx, w in weights:
            nx = x + dx
            if 0 <= nx <= width_minus_1:
                row[nx] += err * w

    def _propagate_error_next_row(
        self,
        next_r: np.ndarray,
        x: int,
        err: float,
        weights: List[Tuple[int, float]],
        width_minus_1: int
    ) -> None:
        for dx, w in weights:
            nx = x + dx
            if 0 <= nx <= width_minus_1:
                next_r[nx] += err * w

    def _atkinson_dither(self, img: Image.Image) -> Image.Image:
        # atkinson dithering spreads error to 6 neighbors with divisor 8
        matrix = [
            (1, 0, 1), (2, 0, 1),
            (-1, 1, 1), (0, 1, 1), (1, 1, 1),
            (0, 2, 1)
        ]
        return self._error_diffusion_dither(img, matrix, 8)

    def _burkes_dither(self, img: Image.Image) -> Image.Image:
        # burkes dithering spreads error to 7 neighbors with divisor 32
        matrix = [
            (1, 0, 8), (2, 0, 4),
            (-2, 1, 2), (-1, 1, 4), (0, 1, 8), (1, 1, 4), (2, 1, 2)
        ]
        return self._error_diffusion_dither(img, matrix, 32)

    def _sierra_dither(self, img: Image.Image) -> Image.Image:
        # sierra dithering spreads error to 10 neighbors across 3 rows
        matrix = [
            (1, 0, 5), (2, 0, 3),
            (-2, 1, 2), (-1, 1, 4), (0, 1, 5), (1, 1, 4), (2, 1, 2),
            (-1, 2, 2), (0, 2, 3), (1, 2, 2)
        ]
        return self._error_diffusion_dither(img, matrix, 32)

    def _stucki_dither(self, img: Image.Image) -> Image.Image:
        # stucki dithering spreads error to 12 neighbors across 3 rows
        matrix = [
            (1, 0, 8), (2, 0, 4),
            (-2, 1, 2), (-1, 1, 4), (0, 1, 8), (1, 1, 4), (2, 1, 2),
            (-2, 2, 1), (-1, 2, 2), (0, 2, 4), (1, 2, 2), (2, 2, 1)
        ]
        return self._error_diffusion_dither(img, matrix, 42)

    def _pad_width(self, img: Image.Image) -> Image.Image:
        # printer protocol requires width divisible by 8 for byte alignment
        if img.width % 8 == 0:
            return img

        new_width = img.width + (8 - img.width % 8)
        padded = Image.new(img.mode, (new_width, img.height), 255)
        padded.paste(img, (0, 0))
        return padded

    def get_preview(
        self,
        image: Image.Image,
        max_width: int = 400,
        max_height: int = 300,
        show_dithering: bool = True
    ) -> Image.Image:
        preview = self.get_full_preview(image, show_dithering)

        scale_w = max_width / preview.width
        scale_h = max_height / preview.height
        scale = min(scale_w, scale_h, 1.0)

        if scale < 1.0:
            new_width = int(preview.width * scale)
            new_height = int(preview.height * scale)
            preview = preview.resize(
                (new_width, new_height),
                Image.Resampling.NEAREST if show_dithering else Image.Resampling.LANCZOS
            )

        return preview

    def get_full_preview(
        self,
        image: Image.Image,
        show_dithering: bool = True
    ) -> Image.Image:
        if show_dithering:
            processed = self.process(image)
            # process inverts for printer protocol so re-invert for visual preview
            preview = ImageOps.invert(processed.convert('L')).convert('RGB')
        else:
            preview = image.copy()
            if preview.mode not in ('RGB', 'L'):
                preview = preview.convert('RGB')

            if self.rotation != 0:
                preview = self._rotate(preview)

            if self.auto_resize:
                preview = self._resize(preview)

            if self.brightness != 1.0:
                preview = self._adjust_brightness(preview)
            if self.contrast != 1.0:
                preview = self._adjust_contrast(preview)

            if self.invert:
                preview = ImageOps.invert(preview.convert('RGB'))

        return preview


def prepare_for_print(
    image: Image.Image,
    brightness: float = DEFAULT_BRIGHTNESS,
    contrast: float = DEFAULT_CONTRAST,
    dither_mode: str = DEFAULT_DITHER_MODE,
    rotation: int = DEFAULT_ROTATION,
    invert: bool = False,
) -> Image.Image:
    processor = ImageProcessor(
        brightness=brightness,
        contrast=contrast,
        dither_mode=dither_mode,
        rotation=rotation,
        invert=invert,
    )
    return processor.process(image)
