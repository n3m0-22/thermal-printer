from typing import Dict, Any, List, Tuple, Optional, Callable

from .defaults import (
    MIN_FONT_SIZE,
    MAX_FONT_SIZE,
    DITHER_MODES,
    ROTATION_OPTIONS,
    APPEARANCE_MODES,
    COLOR_THEMES,
    DEFAULT_PRINTER_WIDTH,
    VALIDATOR_MIN_PRINTER_WIDTH,
    VALIDATOR_MAX_PRINTER_WIDTH,
    VALIDATOR_MIN_RFCOMM_CHANNEL,
    VALIDATOR_MAX_RFCOMM_CHANNEL,
)
from .keys import SettingsKeys
from ..utils.validators import (
    validate_mac_address,
    validate_font_size,
    validate_brightness,
    validate_contrast,
    validate_dither_mode,
    validate_rotation,
)


class ValidationResult:
    def __init__(self, is_valid: bool, errors: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.errors = errors or []

    def __bool__(self) -> bool:
        return self.is_valid

    def add_error(self, error: str) -> None:
        self.errors.append(error)
        self.is_valid = False


class SettingsValidator:
    VALIDATORS: Dict[str, Tuple[Callable[[Any], Tuple[bool, Optional[str]]], bool]] = {
        SettingsKeys.Printer.MAC_ADDRESS: (lambda v: validate_mac_address(v) if v else (True, None), False),
        SettingsKeys.Printer.WIDTH: (lambda v: _validate_printer_width(v), False),
        SettingsKeys.Printer.RFCOMM_CHANNEL: (lambda v: _validate_rfcomm_channel(v), False),
        SettingsKeys.Text.FONT_SIZE: (validate_font_size, False),
        SettingsKeys.Text.ALIGNMENT: (lambda v: _validate_alignment(v), False),
        SettingsKeys.Image.BRIGHTNESS: (validate_brightness, False),
        SettingsKeys.Image.CONTRAST: (validate_contrast, False),
        SettingsKeys.Image.DITHER_MODE: (validate_dither_mode, False),
        SettingsKeys.Image.ROTATION: (validate_rotation, False),
        SettingsKeys.Gui.WINDOW_WIDTH: (lambda v: _validate_positive_int(v, 'Window width'), False),
        SettingsKeys.Gui.WINDOW_HEIGHT: (lambda v: _validate_positive_int(v, 'Window height'), False),
        SettingsKeys.Gui.APPEARANCE_MODE: (lambda v: _validate_appearance_mode(v), False),
        SettingsKeys.Gui.COLOR_THEME: (lambda v: _validate_color_theme(v), False),
        SettingsKeys.Banner.FONT_SIZE: (validate_font_size, False),
        SettingsKeys.Banner.ALIGNMENT: (lambda v: _validate_alignment(v), False),
    }

    @classmethod
    def validate_setting(cls, key: str, value: Any) -> Tuple[bool, Optional[str]]:
        if key in cls.VALIDATORS:
            validator, _ = cls.VALIDATORS[key]
            return validator(value)
        return True, None

    @classmethod
    def validate_section(cls, section: str, values: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult(True)

        for key, value in values.items():
            full_key = f"{section}.{key}"
            is_valid, error = cls.validate_setting(full_key, value)
            if not is_valid:
                result.add_error(f"{key}: {error}")

        return result

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult(True)

        for section, values in config.items():
            if isinstance(values, dict):
                section_result = cls.validate_section(section, values)
                if not section_result.is_valid:
                    for error in section_result.errors:
                        result.add_error(f"{section}.{error}")

        return result

    @classmethod
    def validate_and_fix(
        cls, config: Dict[str, Any], defaults: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[str]]:
        fixed_keys: List[str] = []
        result = config.copy()

        for section, values in config.items():
            if isinstance(values, dict):
                result[section] = values.copy()
                for key, value in values.items():
                    full_key = f"{section}.{key}"
                    is_valid, _ = cls.validate_setting(full_key, value)
                    if not is_valid:
                        if section in defaults and key in defaults[section]:
                            result[section][key] = defaults[section][key]
                            fixed_keys.append(full_key)

        return result, fixed_keys


def _validate_printer_width(value: Any) -> Tuple[bool, Optional[str]]:
    if not isinstance(value, int):
        return False, "Printer width must be an integer"
    if value < VALIDATOR_MIN_PRINTER_WIDTH:
        return False, "Printer width must be positive"
    if value > VALIDATOR_MAX_PRINTER_WIDTH:
        return False, f"Printer width cannot exceed {VALIDATOR_MAX_PRINTER_WIDTH}"
    return True, None


def _validate_rfcomm_channel(value: Any) -> Tuple[bool, Optional[str]]:
    if not isinstance(value, int):
        return False, "RFCOMM channel must be an integer"
    if value < VALIDATOR_MIN_RFCOMM_CHANNEL or value > VALIDATOR_MAX_RFCOMM_CHANNEL:
        return False, f"RFCOMM channel must be between {VALIDATOR_MIN_RFCOMM_CHANNEL} and {VALIDATOR_MAX_RFCOMM_CHANNEL}"
    return True, None


def _validate_positive_int(value: Any, name: str) -> Tuple[bool, Optional[str]]:
    if not isinstance(value, int):
        return False, f"{name} must be an integer"
    if value < 1:
        return False, f"{name} must be positive"
    return True, None


def _validate_alignment(value: Any) -> Tuple[bool, Optional[str]]:
    valid = ['left', 'center', 'right']
    if not isinstance(value, str):
        return False, "Alignment must be a string"
    if value.lower() not in valid:
        return False, f"Alignment must be one of: {', '.join(valid)}"
    return True, None


def _validate_appearance_mode(value: Any) -> Tuple[bool, Optional[str]]:
    if not isinstance(value, str):
        return False, "Appearance mode must be a string"
    if value not in APPEARANCE_MODES:
        return False, f"Appearance mode must be one of: {', '.join(APPEARANCE_MODES)}"
    return True, None


def _validate_color_theme(value: Any) -> Tuple[bool, Optional[str]]:
    if not isinstance(value, str):
        return False, "Color theme must be a string"
    if value not in COLOR_THEMES:
        return False, f"Color theme must be one of: {', '.join(COLOR_THEMES)}"
    return True, None
