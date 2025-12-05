# unicode detection utilities for auto font switching

import unicodedata
from typing import Set

# unicode ranges that require special font support
# these are characters that most default fonts cannot render properly
SPECIAL_UNICODE_RANGES = {
    # math operators
    (0x2200, 0x22FF),  # mathematical operators
    (0x2A00, 0x2AFF),  # supplemental mathematical operators
    (0x27C0, 0x27EF),  # miscellaneous mathematical symbols-A
    (0x2980, 0x29FF),  # miscellaneous mathematical symbols-B
    # superscripts and subscripts
    (0x2070, 0x209F),  # superscripts and subscripts
    # number forms
    (0x2150, 0x218F),  # number forms (fractions)
    # letterlike symbols
    (0x2100, 0x214F),  # letterlike symbols (including ℕ, ℤ, ℚ, ℝ, ℂ)
    # arrows
    (0x2190, 0x21FF),  # arrows
    (0x27F0, 0x27FF),  # supplemental arrows-A
    (0x2900, 0x297F),  # supplemental arrows-B
    (0x2B00, 0x2BFF),  # miscellaneous symbols and arrows
    # general punctuation (includes special dashes, prime symbols)
    (0x2010, 0x2027),  # dashes, quotes, primes
    (0x2030, 0x205E),  # per mille, prime, etc.
    # greek letters (extended)
    (0x0370, 0x03FF),  # greek and coptic
    (0x1F00, 0x1FFF),  # greek extended
    # combining diacritical marks
    (0x0300, 0x036F),  # combining diacritical marks
    (0x20D0, 0x20FF),  # combining diacritical marks for symbols
    # miscellaneous technical
    (0x2300, 0x23FF),  # miscellaneous technical (including angle brackets)
    # geometric shapes
    (0x25A0, 0x25FF),  # geometric shapes
    # miscellaneous symbols
    (0x2600, 0x26FF),  # miscellaneous symbols
    # dingbats
    (0x2700, 0x27BF),  # dingbats
}

# pre-computed set of special codepoints for fast lookup
_SPECIAL_CODEPOINTS: Set[int] = set()
for start, end in SPECIAL_UNICODE_RANGES:
    _SPECIAL_CODEPOINTS.update(range(start, end + 1))

# the fallback font for unicode support (if user preference not available)
# we use fuzzy matching to find this font regardless of naming variations
UNICODE_FALLBACK_FONT_PATTERN = "dejavusans"

# fonts to exclude from fuzzy matching as they dont support all unicode
UNICODE_FONT_EXCLUDE_PATTERNS = [
    "mono",       # dejavu sans mono doesnt support all unicode
    "condensed",  # condensed variants may have issues
]


def find_unicode_font(available_fonts: list, preferred_font: str = "") -> str:

    # first check if preferred font is available
    if preferred_font:
        preferred_lower = preferred_font.lower()
        for font in available_fonts:
            if font.lower() == preferred_lower:
                return font
        # try partial match for preferred font
        for font in available_fonts:
            if preferred_lower in font.lower() or font.lower() in preferred_lower:
                return font

    # fallback to pattern matching
    target = UNICODE_FALLBACK_FONT_PATTERN.lower().replace(" ", "").replace("-", "")

    candidates = []
    for font in available_fonts:
        normalized = font.lower().replace(" ", "").replace("-", "")

        if target in normalized or normalized in target:
            # check exclusions
            excluded = False
            for exclude in UNICODE_FONT_EXCLUDE_PATTERNS:
                if exclude in normalized:
                    excluded = True
                    break

            if not excluded:
                candidates.append(font)

    # prefer shorter names to get base font over variants
    if candidates:
        candidates.sort(key=len)
        return candidates[0]

    return ""


def is_special_unicode_char(char: str) -> bool:
    if len(char) != 1:
        return False
    codepoint = ord(char)
    return codepoint in _SPECIAL_CODEPOINTS


def contains_special_unicode(text: str) -> bool:
    for char in text:
        if is_special_unicode_char(char):
            return True
    return False


def get_special_unicode_chars(text: str) -> str:
    return ''.join(char for char in text if is_special_unicode_char(char))


def get_unicode_category_name(char: str) -> str:
    try:
        return unicodedata.name(char, "UNKNOWN")
    except ValueError:
        return "UNKNOWN"


def describe_unicode_content(text: str) -> str:
    categories = set()

    for char in text:
        codepoint = ord(char)

        if 0x2200 <= codepoint <= 0x22FF or 0x2A00 <= codepoint <= 0x2AFF:
            categories.add("math operators")
        elif 0x2070 <= codepoint <= 0x209F:
            categories.add("superscripts/subscripts")
        elif 0x2150 <= codepoint <= 0x218F:
            categories.add("fractions")
        elif 0x2100 <= codepoint <= 0x214F:
            categories.add("number sets (ℕ, ℤ, ℚ, ℝ, ℂ)")
        elif 0x2190 <= codepoint <= 0x21FF or 0x27F0 <= codepoint <= 0x27FF:
            categories.add("arrows")
        elif 0x0370 <= codepoint <= 0x03FF:
            categories.add("greek letters")
        elif 0x0300 <= codepoint <= 0x036F:
            categories.add("combining marks")

    if categories:
        return ", ".join(sorted(categories))
    return "special symbols"
