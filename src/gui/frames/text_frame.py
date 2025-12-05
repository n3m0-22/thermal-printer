# text input and formatting frame for text printing

from typing import Optional, Callable

from .base_text_frame import BaseTextFrame


class TextFrame(BaseTextFrame):
    # frame for standard text printing with horizontal alignment

    _settings_section = "text"
    _save_dialog_title = "Save Text Template"
    _print_status_message = "Sending text to printer..."
    _preview_landscape = False
    _renderer_wrap = True
