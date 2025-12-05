# unicode text renderer with automatic font fallback
# renders text character-by-character, using fallback fonts for missing glyphs

from typing import Optional, Tuple, List
from PIL import ImageDraw, ImageFont
import unicodedata

from .font_manager import get_font_manager, FontManager


class UnicodeTextRenderer:
    """Renders text with automatic font fallback for Unicode characters."""

    def __init__(self, font_manager: Optional[FontManager] = None):
        self._font_manager = font_manager or get_font_manager()

    def draw_text(
        self,
        draw: ImageDraw.ImageDraw,
        position: Tuple[int, int],
        text: str,
        font: ImageFont.FreeTypeFont,
        fill=(0, 0, 0),
        size: Optional[int] = None
    ) -> float:
        """Draw text with font fallback for unsupported characters.

        Returns width of rendered text.
        """
        if not text:
            return 0

        if size is None:
            size = getattr(font, 'size', 24)

        x, y = position
        total_width = 0

        # build font map for all characters
        char_fonts = self._font_manager.get_char_font_map(text, font, size)

        # group consecutive characters with same font for efficiency
        segments = self._group_by_font(text, char_fonts)

        for segment_text, segment_font in segments:
            if not segment_text:
                continue

            draw.text((x + total_width, y), segment_text, fill=fill, font=segment_font)

            # advance position
            try:
                segment_width = segment_font.getlength(segment_text)
            except Exception:
                # fallback width estimation
                segment_width = len(segment_text) * size * 0.6

            total_width += segment_width

        return total_width

    def get_text_width(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        size: Optional[int] = None
    ) -> float:
        if not text:
            return 0

        if size is None:
            size = getattr(font, 'size', 24)

        char_fonts = self._font_manager.get_char_font_map(text, font, size)
        segments = self._group_by_font(text, char_fonts)

        total_width = 0
        for segment_text, segment_font in segments:
            if not segment_text:
                continue
            try:
                total_width += segment_font.getlength(segment_text)
            except Exception:
                # fallback width estimation
                total_width += len(segment_text) * size * 0.6

        return total_width

    def draw_text_multiline(
        self,
        draw: ImageDraw.ImageDraw,
        position: Tuple[int, int],
        text: str,
        font: ImageFont.FreeTypeFont,
        fill=(0, 0, 0),
        size: Optional[int] = None,
        line_spacing: float = 1.2,
        alignment: str = "left",
        max_width: Optional[int] = None
    ) -> Tuple[float, float]:
        """Draw multiline text with font fallback.

        Returns tuple of (max_width, total_height) of rendered text.
        """
        if not text:
            return (0, 0)

        if size is None:
            size = getattr(font, 'size', 24)

        x, y = position
        lines = text.split('\n')
        line_height = int(size * line_spacing)

        max_line_width = 0
        y_offset = 0

        for line in lines:
            if not line:
                y_offset += line_height
                continue

            line_width = self.get_text_width(line, font, size)
            max_line_width = max(max_line_width, line_width)

            if alignment == "center":
                line_x = x - (line_width / 2)
            elif alignment == "right":
                line_x = x - line_width
            else:
                line_x = x

            self.draw_text(draw, (line_x, y + y_offset), line, font, fill, size)
            y_offset += line_height

        return (max_line_width, y_offset)

    def _group_by_font(
        self,
        text: str,
        char_fonts: dict
    ) -> List[Tuple[str, ImageFont.FreeTypeFont]]:
        """Group consecutive characters that use the same font for efficiency."""
        if not text:
            return []

        segments = []
        current_segment = ""
        current_font = None

        for char in text:
            char_font = char_fonts.get(char)

            if current_font is None:
                current_font = char_font
                current_segment = char
            elif char_font is current_font:
                current_segment += char
            else:
                # font changed so save segment and start new one
                if current_segment:
                    segments.append((current_segment, current_font))
                current_segment = char
                current_font = char_font

        if current_segment and current_font:
            segments.append((current_segment, current_font))

        return segments

    def normalize_unicode(self, text: str) -> str:
        """Normalize unicode text for consistent rendering using NFC composition."""
        return unicodedata.normalize('NFC', text)


# module-level singleton
_unicode_renderer: Optional[UnicodeTextRenderer] = None


def get_unicode_renderer() -> UnicodeTextRenderer:
    global _unicode_renderer
    if _unicode_renderer is None:
        _unicode_renderer = UnicodeTextRenderer()
    return _unicode_renderer


def draw_unicode_text(
    draw: ImageDraw.ImageDraw,
    position: Tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill=(0, 0, 0),
    size: Optional[int] = None
) -> float:
    renderer = get_unicode_renderer()
    text = renderer.normalize_unicode(text)
    return renderer.draw_text(draw, position, text, font, fill, size)


def draw_unicode_text_multiline(
    draw: ImageDraw.ImageDraw,
    position: Tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill=(0, 0, 0),
    size: Optional[int] = None,
    line_spacing: float = 1.2,
    alignment: str = "left"
) -> Tuple[float, float]:
    renderer = get_unicode_renderer()
    text = renderer.normalize_unicode(text)
    return renderer.draw_text_multiline(
        draw, position, text, font, fill, size, line_spacing, alignment
    )


def get_unicode_text_width(
    text: str,
    font: ImageFont.FreeTypeFont,
    size: Optional[int] = None
) -> float:
    renderer = get_unicode_renderer()
    text = renderer.normalize_unicode(text)
    return renderer.get_text_width(text, font, size)
