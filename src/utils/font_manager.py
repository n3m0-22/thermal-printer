"""Font management utilities for Linux systems.

This module handles font discovery, loading, and Unicode character support.
It scans system font directories, caches loaded fonts for performance, and
provides fallback mechanisms for Unicode characters not present in the
primary font.

Font loading is expensive due to filesystem access and font parsing. This module
uses multiple cache layers: _font_cache for loaded ImageFont objects keyed by
(family, size, bold, italic), _fallback_font_cache for Unicode fallback fonts,
and _glyph_cache for character existence checks. The global singleton ensures
font scanning happens only once per process.
"""

import os
import glob
import logging
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass

from PIL import ImageFont

# project fonts directory (relative to project root)
PROJECT_FONTS_DIR = Path(__file__).parent.parent.parent / "fonts"

from ..config.defaults import (
    LINUX_FONT_PATHS,
    PREFERRED_FONTS,
    FALLBACK_FONTS,
    UNICODE_FALLBACK_FONTS,
    DEFAULT_FONT_SIZE,
    DEFAULT_FONT_FAMILY,
)
from ..core.exceptions import FontNotFoundError

logger = logging.getLogger(__name__)


# additional font paths for various systems
EXTRA_FONT_PATHS = [
    # linux truetype and opentype
    "/usr/share/fonts/truetype",
    "/usr/share/fonts/opentype",
    "/usr/share/fonts/TTF",
    "/usr/share/fonts/OTF",
    # linux specific font packages
    "/usr/share/fonts/google-droid",
    "/usr/share/fonts/droid",
    "/usr/share/fonts/noto",
    "/usr/share/fonts/liberation",
    "/usr/share/fonts/dejavu",
    "/usr/share/fonts/gnu-free",
    "/usr/share/fonts/freefont",
    # microsoft core fonts (often installed on linux)
    "/usr/share/fonts/truetype/msttcorefonts",
    "/usr/share/fonts/corefonts",
]


@dataclass
class FontInfo:
    """Information about a discovered font file."""
    name: str
    path: str
    family: str
    style: str


class FontManager:
    """Manages system fonts and Unicode fallback support.

    Scans system directories for fonts, provides font loading with style
    matching, and handles Unicode character rendering with automatic
    fallback to fonts that support missing characters.
    """
    def __init__(self):
        self._fonts: Dict[str, FontInfo] = {}
        self._font_families: Dict[str, List[FontInfo]] = {}
        self._fallback_fonts: List[ImageFont.FreeTypeFont] = []
        self._fallback_font_cache: Dict[int, Dict[str, ImageFont.FreeTypeFont]] = {}
        self._glyph_cache: Dict[str, Dict[str, bool]] = {}
        # cache loaded fonts to avoid repeated disk access
        self._font_cache: Dict[Tuple[str, int, bool, bool], ImageFont.FreeTypeFont] = {}
        self._scan_fonts()

    def _scan_fonts(self) -> None:
        font_extensions = ['*.ttf', '*.otf', '*.TTF', '*.OTF', '*.ttc', '*.TTC']

        # include project fonts directory first (higher priority)
        all_paths = []
        if PROJECT_FONTS_DIR.is_dir():
            all_paths.append(str(PROJECT_FONTS_DIR))
        all_paths.extend(LINUX_FONT_PATHS)
        all_paths.extend(EXTRA_FONT_PATHS)

        for font_dir in all_paths:
            if not os.path.isdir(font_dir):
                continue

            for ext in font_extensions:
                pattern = os.path.join(font_dir, '**', ext)
                for font_path in glob.glob(pattern, recursive=True):
                    self._register_font(font_path)

    def _register_font(self, path: str) -> None:
        try:
            filename = os.path.basename(path)
            name_without_ext = os.path.splitext(filename)[0]
            family, style = self._parse_font_name(name_without_ext)

            font_info = FontInfo(
                name=name_without_ext,
                path=path,
                family=family,
                style=style
            )

            self._fonts[name_without_ext.lower()] = font_info

            family_lower = family.lower()
            if family_lower not in self._font_families:
                self._font_families[family_lower] = []
            self._font_families[family_lower].append(font_info)

        except (OSError, ValueError) as e:
            logger.debug(f"could not register font {path}: {e}")

    def _parse_font_name(self, name: str) -> Tuple[str, str]:
        style = "Regular"
        family = name

        style_markers = [
            ("-BoldItalic", "BoldItalic"),
            ("-BoldOblique", "BoldItalic"),
            ("-Bold", "Bold"),
            ("-Italic", "Italic"),
            ("-Oblique", "Italic"),
            ("-Regular", "Regular"),
            ("BoldItalic", "BoldItalic"),
            ("BoldOblique", "BoldItalic"),
            ("Bold", "Bold"),
            ("Italic", "Italic"),
            ("Oblique", "Italic"),
            ("Regular", "Regular"),
        ]

        for marker, style_name in style_markers:
            if name.endswith(marker):
                family = name[:-len(marker)].rstrip('-_ ')
                style = style_name
                break

        family = family.replace('-', ' ').replace('_', ' ')
        return family, style

    def get_available_families(self) -> List[str]:
        families = set()
        for family_list in self._font_families.values():
            for font_info in family_list:
                families.add(font_info.family)
        return sorted(families)

    def get_family_styles(self, family: str) -> List[str]:
        family_lower = family.lower()
        if family_lower not in self._font_families:
            return []

        styles = set()
        for font_info in self._font_families[family_lower]:
            styles.add(font_info.style)
        return sorted(styles)

    def get_font_path(
        self,
        family: str,
        style: str = "Regular",
        fallback: bool = True
    ) -> Optional[str]:
        family_lower = family.lower()

        if family_lower in self._font_families:
            for font_info in self._font_families[family_lower]:
                if font_info.style == style:
                    return font_info.path

            if self._font_families[family_lower]:
                return self._font_families[family_lower][0].path

        if fallback:
            for preferred in PREFERRED_FONTS:
                preferred_lower = preferred.lower()
                if preferred_lower in self._font_families:
                    for font_info in self._font_families[preferred_lower]:
                        if font_info.style == style:
                            return font_info.path
                    if self._font_families[preferred_lower]:
                        return self._font_families[preferred_lower][0].path

        return None

    def load_font(
        self,
        family: str = DEFAULT_FONT_FAMILY,
        size: int = DEFAULT_FONT_SIZE,
        bold: bool = False,
        italic: bool = False
    ) -> ImageFont.FreeTypeFont:
        """Load a font with specified parameters.

        Uses cache to avoid repeated disk access. Tries to match requested
        style, falling back to available styles if exact match not found.
        """
        # check cache first
        cache_key = (family.lower(), size, bold, italic)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        if bold and italic:
            styles_to_try = ["BoldItalic", "BoldOblique", "Bold", "Italic", "Regular"]
        elif bold:
            styles_to_try = ["Bold", "Medium", "SemiBold", "Regular"]
        elif italic:
            styles_to_try = ["Italic", "Oblique", "LightItalic", "Regular"]
        else:
            styles_to_try = ["Regular", "Book", "Normal", "Medium"]

        font_path = None
        for style in styles_to_try:
            font_path = self.get_font_path(family, style, fallback=False)
            if font_path:
                break

        if font_path is None:
            font_path = self.get_font_path(family, styles_to_try[0], fallback=True)

        if font_path is None:
            # try ultimate fallback fonts
            for fallback in FALLBACK_FONTS:
                font_path = self.get_font_path(fallback, "Regular", fallback=False)
                if font_path:
                    break

        if font_path is None:
            # last resort use pillow default
            try:
                font = ImageFont.load_default()
                self._font_cache[cache_key] = font
                return font
            except (OSError, ImportError) as e:
                raise FontNotFoundError(f"cannot find font: {family}") from e

        try:
            font = ImageFont.truetype(font_path, size)
            self._font_cache[cache_key] = font
            return font
        except (OSError, IOError) as e:
            # if specific font fails try pillow default
            try:
                font = ImageFont.load_default()
                self._font_cache[cache_key] = font
                return font
            except (OSError, ImportError):
                raise FontNotFoundError(f"cannot load font {font_path}: {e}")

    def find_font_file(self, name: str) -> Optional[str]:
        name_lower = name.lower()

        if name_lower in self._fonts:
            return self._fonts[name_lower].path

        for font_name, font_info in self._fonts.items():
            if name_lower in font_name:
                return font_info.path

        return None

    def font_has_glyph(self, font: ImageFont.FreeTypeFont, char: str) -> bool:
        """Check if a font has a glyph for a character using PIL's getmask."""
        if not char or char == ' ':
            return True

        # cache check using font path and character
        font_path = getattr(font, 'path', str(id(font)))
        if font_path not in self._glyph_cache:
            self._glyph_cache[font_path] = {}
        if char in self._glyph_cache[font_path]:
            return self._glyph_cache[font_path][char]

        try:
            # getmask returns empty mask for missing glyphs
            mask = font.getmask(char)
            has_glyph = mask.size[0] > 0 and mask.size[1] > 0
            self._glyph_cache[font_path][char] = has_glyph
            return has_glyph
        except (OSError, AttributeError, ValueError) as e:
            logger.debug(f"error checking glyph for {char}: {e}")
            self._glyph_cache[font_path][char] = False
            return False

    def get_unicode_fallback_fonts(self, size: int) -> List[ImageFont.FreeTypeFont]:
        if size in self._fallback_font_cache:
            return list(self._fallback_font_cache[size].values())

        self._fallback_font_cache[size] = {}
        fonts = []

        for family in UNICODE_FALLBACK_FONTS:
            font_path = self.get_font_path(family, "Regular", fallback=False)
            if font_path:
                try:
                    font = ImageFont.truetype(font_path, size)
                    fonts.append(font)
                    self._fallback_font_cache[size][family] = font
                except (OSError, IOError) as e:
                    logger.debug(f"could not load fallback font {family}: {e}")

        return fonts

    def find_font_for_char(
        self,
        char: str,
        primary_font: ImageFont.FreeTypeFont,
        size: int
    ) -> ImageFont.FreeTypeFont:
        if self.font_has_glyph(primary_font, char):
            return primary_font

        # search fallback fonts
        fallbacks = self.get_unicode_fallback_fonts(size)
        for font in fallbacks:
            if self.font_has_glyph(font, char):
                return font

        # no fallback found so return primary (will show placeholder)
        return primary_font

    def get_char_font_map(
        self,
        text: str,
        primary_font: ImageFont.FreeTypeFont,
        size: int
    ) -> Dict[str, ImageFont.FreeTypeFont]:
        """Build a map of character to best font for rendering.

        Optimizes by caching results and lazy-loading fallback fonts.
        """
        char_fonts = {}
        fallbacks = None

        for char in text:
            if char in char_fonts:
                continue

            if char == ' ' or self.font_has_glyph(primary_font, char):
                char_fonts[char] = primary_font
            else:
                # lazy load fallbacks only when needed
                if fallbacks is None:
                    fallbacks = self.get_unicode_fallback_fonts(size)

                found = False
                for font in fallbacks:
                    if self.font_has_glyph(font, char):
                        char_fonts[char] = font
                        found = True
                        break

                if not found:
                    char_fonts[char] = primary_font

        return char_fonts


_font_manager: Optional[FontManager] = None


def get_font_manager() -> FontManager:
    global _font_manager
    if _font_manager is None:
        _font_manager = FontManager()
    return _font_manager
