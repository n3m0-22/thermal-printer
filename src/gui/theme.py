# centralized theme and font management for consistent UI styling

from typing import Optional
import customtkinter as ctk

from ..config.defaults import (
    FONT_SIZE_SMALL,
    FONT_SIZE_NORMAL,
    FONT_SIZE_LARGE,
    FONT_SIZE_XLARGE,
    FONT_SIZE_TITLE,
    FONT_SIZE_HEADER,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_BOLD,
    FONT_MONOSPACE_SIZE,
    UI_BUTTON_WIDTH,
    UI_BUTTON_HEIGHT,
    BUTTON_PRINT_FG,
    BUTTON_PRINT_HOVER,
    BUTTON_DELETE_FG,
    BUTTON_DELETE_HOVER,
)


class AppFonts:
    _cache: dict = {}

    @classmethod
    def _get_or_create(
        cls,
        key: str,
        size: int,
        weight: str = FONT_WEIGHT_NORMAL,
        family: Optional[str] = None
    ) -> ctk.CTkFont:
        if key not in cls._cache:
            kwargs = {"size": size, "weight": weight}
            if family:
                kwargs["family"] = family
            cls._cache[key] = ctk.CTkFont(**kwargs)
        return cls._cache[key]

    @classmethod
    def clear_cache(cls) -> None:
        # useful when switching between light and dark themes
        cls._cache.clear()

    # standard text fonts
    @classmethod
    def small(cls) -> ctk.CTkFont:
        return cls._get_or_create("small", FONT_SIZE_SMALL)

    @classmethod
    def normal(cls) -> ctk.CTkFont:
        return cls._get_or_create("normal", FONT_SIZE_NORMAL)

    @classmethod
    def large(cls) -> ctk.CTkFont:
        return cls._get_or_create("large", FONT_SIZE_LARGE)

    @classmethod
    def xlarge(cls) -> ctk.CTkFont:
        return cls._get_or_create("xlarge", FONT_SIZE_XLARGE)

    # label fonts
    @classmethod
    def label(cls) -> ctk.CTkFont:
        return cls._get_or_create("label", FONT_SIZE_NORMAL, FONT_WEIGHT_BOLD)

    @classmethod
    def label_small(cls) -> ctk.CTkFont:
        return cls._get_or_create("label_small", FONT_SIZE_SMALL, FONT_WEIGHT_BOLD)

    # title and header fonts
    @classmethod
    def title(cls) -> ctk.CTkFont:
        return cls._get_or_create("title", FONT_SIZE_TITLE, FONT_WEIGHT_BOLD)

    @classmethod
    def header(cls) -> ctk.CTkFont:
        return cls._get_or_create("header", FONT_SIZE_HEADER, FONT_WEIGHT_BOLD)

    @classmethod
    def section(cls) -> ctk.CTkFont:
        return cls._get_or_create("section", FONT_SIZE_LARGE, FONT_WEIGHT_BOLD)

    # control fonts
    @classmethod
    def button(cls) -> ctk.CTkFont:
        return cls._get_or_create("button", FONT_SIZE_NORMAL)

    @classmethod
    def control(cls) -> ctk.CTkFont:
        return cls._get_or_create("control", FONT_SIZE_NORMAL)

    # monospace font
    @classmethod
    def monospace(cls) -> ctk.CTkFont:
        return cls._get_or_create("monospace", FONT_MONOSPACE_SIZE, family="monospace")

    # tab button font
    @classmethod
    def tab(cls) -> ctk.CTkFont:
        return cls._get_or_create("tab", FONT_SIZE_NORMAL, FONT_WEIGHT_BOLD)


class ButtonStyles:
    """Pre-configured button style dictionaries for common button types."""

    @staticmethod
    def standard(
        width: int = UI_BUTTON_WIDTH,
        height: int = UI_BUTTON_HEIGHT
    ) -> dict:
        return {
            "width": width,
            "height": height,
            "font": AppFonts.button()
        }

    @staticmethod
    def print_button(
        width: int = UI_BUTTON_WIDTH,
        height: int = UI_BUTTON_HEIGHT
    ) -> dict:
        return {
            "width": width,
            "height": height,
            "font": AppFonts.button(),
            "fg_color": BUTTON_PRINT_FG,
            "hover_color": BUTTON_PRINT_HOVER
        }

    @staticmethod
    def delete_button(
        width: int = UI_BUTTON_WIDTH,
        height: int = UI_BUTTON_HEIGHT
    ) -> dict:
        return {
            "width": width,
            "height": height,
            "font": AppFonts.button(),
            "fg_color": BUTTON_DELETE_FG,
            "hover_color": BUTTON_DELETE_HOVER
        }

    @staticmethod
    def small(width: int = 80, height: int = 32) -> dict:
        return {
            "width": width,
            "height": height,
            "font": AppFonts.small()
        }

    @staticmethod
    def icon_button(size: int = 36) -> dict:
        return {
            "width": size,
            "height": size,
            "font": AppFonts.normal()
        }


def get_paned_bg_color() -> str:
    # customtkinter appearance mode determines paned window background
    from ..config.defaults import CANVAS_PANED_BG_LIGHT, CANVAS_PANED_BG_DARK
    if ctk.get_appearance_mode() == "Dark":
        return CANVAS_PANED_BG_DARK
    return CANVAS_PANED_BG_LIGHT
