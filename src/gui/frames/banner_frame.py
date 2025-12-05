# banner text input and formatting frame for banner printing

from typing import Optional, Callable, List, Tuple

from PIL import Image

from .base_text_frame import BaseTextFrame
from ...config.defaults import (
    DEFAULT_PRINTER_WIDTH,
    TEXT_ALIGN_LEFT,
    TEXT_ALIGN_CENTER,
    TEXT_ALIGN_RIGHT,
)


class BannerFrame(BaseTextFrame):
    # frame for banner printing with vertical alignment and rotation

    _settings_section = "banner"
    _save_dialog_title = "Save Banner Template"
    _print_status_message = "Sending banner to printer..."
    _preview_landscape = True
    _renderer_wrap = False
    _templates_dir = "gallery/banner"

    def _get_alignment_options(self) -> List[Tuple[str, str]]:
        # banner uses vertical alignment labels
        return [
            ("Bottom", TEXT_ALIGN_LEFT),
            ("Center", TEXT_ALIGN_CENTER),
            ("Top", TEXT_ALIGN_RIGHT),
        ]

    def _on_alignment_change(self) -> None:
        self._save_settings()
        self._update_preview()

    def _get_current_settings(self) -> dict:
        settings = super()._get_current_settings()
        settings["type"] = "banner"
        return settings

    def _apply_vertical_alignment(self, img: Image.Image) -> Image.Image:
        # printer width becomes height after 90 degree rotation
        target_height = DEFAULT_PRINTER_WIDTH
        current_height = img.height

        if current_height >= target_height:
            return img

        aligned = Image.new('RGB', (img.width, target_height), color=(255, 255, 255))

        align = self.align_var.get()
        if align == TEXT_ALIGN_LEFT:
            y_offset = target_height - current_height
        elif align == TEXT_ALIGN_CENTER:
            y_offset = (target_height - current_height) // 2
        else:
            y_offset = 0

        aligned.paste(img, (0, y_offset))
        return aligned

    def _process_image_for_preview(self, rgb_image):
        return self._apply_vertical_alignment(rgb_image)

    def _process_image_for_print(self, rgb_image):
        rgb_image = self._apply_vertical_alignment(rgb_image)
        # rotate 90ccw so horizontal preview prints vertically
        return rgb_image.transpose(Image.Transpose.ROTATE_90)
