# text to image rendering for thermal printing

from typing import Optional
from PIL import Image, ImageDraw, ImageFont, ImageChops

from ..config.defaults import (
    DEFAULT_FONT_SIZE,
    DEFAULT_FONT_FAMILY,
    DEFAULT_TEXT_ALIGN,
    TEXT_ALIGN_LEFT,
    TEXT_ALIGN_CENTER,
    TEXT_ALIGN_RIGHT,
)
from ..core.protocol import PrinterProtocol
from ..utils.font_manager import get_font_manager


class TextRenderer:
    def __init__(
        self,
        width: int = PrinterProtocol.PRINTER_WIDTH,
        font_family: str = DEFAULT_FONT_FAMILY,
        font_size: int = DEFAULT_FONT_SIZE,
        bold: bool = False,
        italic: bool = False,
        alignment: str = DEFAULT_TEXT_ALIGN,
        wrap: bool = True,
    ):
        self.width = width
        self.font_family = font_family
        self.font_size = font_size
        self.bold = bold
        self.italic = italic
        self.alignment = alignment
        self.wrap = wrap

        self._font: Optional[ImageFont.FreeTypeFont] = None
        self._load_font()

    def _load_font(self) -> None:
        font_manager = get_font_manager()
        self._font = font_manager.load_font(
            family=self.font_family,
            size=self.font_size,
            bold=self.bold,
            italic=self.italic
        )

    def update_font(
        self,
        font_family: Optional[str] = None,
        font_size: Optional[int] = None,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
    ) -> None:
        if font_family is not None:
            self.font_family = font_family
        if font_size is not None:
            self.font_size = font_size
        if bold is not None:
            self.bold = bold
        if italic is not None:
            self.italic = italic

        self._load_font()

    def set_alignment(self, alignment: str) -> None:
        if alignment in (TEXT_ALIGN_LEFT, TEXT_ALIGN_CENTER, TEXT_ALIGN_RIGHT):
            self.alignment = alignment

    def wrap_text(self, text: str) -> str:
        if not self._font:
            return text

        lines = []
        for paragraph in text.split('\n'):
            if not paragraph.strip():
                lines.append('')
                continue

            wrapped = self._wrap_paragraph(paragraph)
            lines.append(wrapped)

        return '\n'.join(lines)

    def _wrap_paragraph(self, text: str) -> str:
        if not self._font:
            return text

        words = text.split()
        if not words:
            return ''

        lines = ['']

        for word in words:
            test_line = f'{lines[-1]} {word}'.strip()
            line_width = self._font.getlength(test_line)

            if line_width <= self.width:
                lines[-1] = test_line
            else:
                if lines[-1]:
                    lines.append(word)
                else:
                    lines[-1] = word

        return '\n'.join(lines)

    def render(self, text: str, max_height: int = 5000) -> Image.Image:
        if not text.strip():
            return Image.new('RGB', (self.width, 10), color=(255, 255, 255))

        if self.wrap:
            render_text = self.wrap_text(text)
        else:
            render_text = text

        # left padding accounts for fonts with negative left side bearing
        left_padding = 10 if not self.wrap else 0

        if self.wrap:
            img_width = self.width
        else:
            max_line_width = 0
            for line in render_text.split('\n'):
                if self._font and line:
                    line_width = self._font.getlength(line)
                    max_line_width = max(max_line_width, line_width)
            img_width = max(int(max_line_width) + 20 + left_padding, self.width)

        img = Image.new('RGB', (img_width, max_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        y_position = 0
        line_spacing = int(self.font_size * 1.2)

        for line in render_text.split('\n'):
            if not line:
                y_position += line_spacing
                continue

            if self._font:
                line_width = self._font.getlength(line)
            else:
                line_width = len(line) * (self.font_size // 2)

            if self.alignment == TEXT_ALIGN_CENTER:
                x_position = (img_width - line_width) // 2
            elif self.alignment == TEXT_ALIGN_RIGHT:
                x_position = img_width - line_width
            else:
                x_position = left_padding

            draw.text(
                (x_position, y_position),
                line,
                fill=(0, 0, 0),
                font=self._font
            )

            y_position += line_spacing

        return self._trim_image(img)

    def _trim_image(self, img: Image.Image, padding: int = 10) -> Image.Image:
        bg = Image.new(img.mode, img.size, (255, 255, 255))
        diff = ImageChops.difference(img, bg)
        diff = ImageChops.add(diff, diff, 2.0)
        bbox = diff.getbbox()

        if bbox:
            left, top, right, bottom = bbox
            if self.wrap:
                return img.crop((0, 0, self.width, min(bottom + padding, img.height)))
            else:
                return img.crop((0, 0, min(right + padding, img.width), min(bottom + padding, img.height)))

        return Image.new('RGB', (self.width, padding), color=(255, 255, 255))

    def get_preview(self, text: str, max_width: int = 400, max_height: int = 300) -> Image.Image:
        full_image = self.render(text)

        scale_w = max_width / full_image.width
        scale_h = max_height / full_image.height
        scale = min(scale_w, scale_h, 1.0)

        if scale < 1.0:
            new_width = int(full_image.width * scale)
            new_height = int(full_image.height * scale)
            return full_image.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS
            )

        return full_image


def render_text(
    text: str,
    font_family: str = DEFAULT_FONT_FAMILY,
    font_size: int = DEFAULT_FONT_SIZE,
    bold: bool = False,
    italic: bool = False,
    alignment: str = DEFAULT_TEXT_ALIGN,
) -> Image.Image:
    renderer = TextRenderer(
        font_family=font_family,
        font_size=font_size,
        bold=bold,
        italic=italic,
        alignment=alignment
    )
    return renderer.render(text)
