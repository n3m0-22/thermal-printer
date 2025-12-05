# input validation utilities

import re
from typing import Optional, Tuple

from ..config.defaults import (
    MIN_FONT_SIZE,
    MAX_FONT_SIZE,
    DITHER_MODES,
    ROTATION_OPTIONS,
    VALIDATOR_MIN_BRIGHTNESS,
    VALIDATOR_MAX_BRIGHTNESS,
    VALIDATOR_MIN_CONTRAST,
    VALIDATOR_MAX_CONTRAST,
    MAC_ADDRESS_BYTE_COUNT,
    MAC_ADDRESS_PAIR_SIZE,
    MAC_ADDRESS_PAIR_STEP,
)


def validate_mac_address(mac: str) -> Tuple[bool, Optional[str]]:
    if not mac:
        return False, "MAC address is required"

    pattern = r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$'
    if re.match(pattern, mac):
        return True, None

    pattern_dash = r'^([0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}$'
    if re.match(pattern_dash, mac):
        return True, None

    return False, "Invalid MAC address format. Expected: XX:XX:XX:XX:XX:XX"


def normalize_mac_address(mac: str) -> str:
    clean = mac.replace(':', '').replace('-', '').upper()
    return ':'.join(clean[i:i+MAC_ADDRESS_PAIR_SIZE] for i in range(0, MAC_ADDRESS_BYTE_COUNT, MAC_ADDRESS_PAIR_STEP))


def validate_font_size(size: int) -> Tuple[bool, Optional[str]]:
    if not isinstance(size, (int, float)):
        return False, "Font size must be a number"

    size = int(size)

    if size < MIN_FONT_SIZE:
        return False, f"Font size must be at least {MIN_FONT_SIZE}"

    if size > MAX_FONT_SIZE:
        return False, f"Font size cannot exceed {MAX_FONT_SIZE}"

    return True, None


def validate_brightness(value: float) -> Tuple[bool, Optional[str]]:
    if not isinstance(value, (int, float)):
        return False, "Brightness must be a number"

    if value < VALIDATOR_MIN_BRIGHTNESS:
        return False, "Brightness cannot be negative"

    if value > VALIDATOR_MAX_BRIGHTNESS:
        return False, f"Brightness cannot exceed {VALIDATOR_MAX_BRIGHTNESS}"

    return True, None


def validate_contrast(value: float) -> Tuple[bool, Optional[str]]:
    if not isinstance(value, (int, float)):
        return False, "Contrast must be a number"

    if value < VALIDATOR_MIN_CONTRAST:
        return False, "Contrast cannot be negative"

    if value > VALIDATOR_MAX_CONTRAST:
        return False, f"Contrast cannot exceed {VALIDATOR_MAX_CONTRAST}"

    return True, None


def validate_dither_mode(mode: str) -> Tuple[bool, Optional[str]]:
    if mode.lower() not in [m.lower() for m in DITHER_MODES]:
        valid_modes = ", ".join(DITHER_MODES)
        return False, f"Invalid dither mode. Valid options: {valid_modes}"

    return True, None


def validate_rotation(degrees: int) -> Tuple[bool, Optional[str]]:
    if degrees not in ROTATION_OPTIONS:
        valid_angles = ", ".join(str(r) for r in ROTATION_OPTIONS)
        return False, f"Invalid rotation. Valid options: {valid_angles}"

    return True, None


def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))


def sanitize_filename(filename: str) -> str:
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    filename = filename.strip('. ')

    if not filename:
        filename = "untitled"

    return filename


def is_valid_image_extension(filepath: str) -> bool:
    valid_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif'}
    ext = filepath.lower().rsplit('.', 1)[-1] if '.' in filepath else ''
    return f'.{ext}' in valid_extensions


def is_valid_text_extension(filepath: str) -> bool:
    valid_extensions = {'.txt', '.md', '.text'}
    ext = filepath.lower().rsplit('.', 1)[-1] if '.' in filepath else ''
    return f'.{ext}' in valid_extensions or ext == ''
