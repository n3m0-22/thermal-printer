# preview canvas with paper simulation and scrolling

from typing import Optional, TYPE_CHECKING
import customtkinter as ctk
from tkinter import Canvas

if TYPE_CHECKING:
    from ...gui.interfaces import SettingsService

from ...utils.pil_compat import Image, PhotoImage, is_imagetk_available

from ...config.defaults import (
    PREVIEW_PAPER_WIDTH,
    PREVIEW_MIN_SIDEBAR_WIDTH,
    PREVIEW_PAPER_BORDER_WIDTH,
    PREVIEW_SIDEBAR_COLOR_LIGHT,
    PREVIEW_SIDEBAR_COLOR_DARK,
    PREVIEW_MIN_SCALE,
    PREVIEW_MAX_SCALE,
    DEFAULT_PREVIEW_SCALE,
    PREVIEW_PAPER_PADDING,
    PREVIEW_FALLBACK_WIDTH,
    PREVIEW_FALLBACK_HEIGHT,
    PREVIEW_SCROLL_UNITS,
    PREVIEW_PLACEHOLDER_FONT,
    PREVIEW_PLACEHOLDER_FONT_SIZE,
    PREVIEW_PLACEHOLDER_TEXT,
    PREVIEW_PLACEHOLDER_COLOR,
)
from ...config.settings import get_settings
from ...config.keys import SettingsKeys


class PreviewCanvas(ctk.CTkFrame):

    def __init__(
        self,
        master,
        min_height: int = 150,
        landscape: bool = False,
        settings_service: Optional["SettingsService"] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)

        self.min_height = min_height
        self._landscape = landscape
        self._image: Optional[Image.Image] = None
        self._photo_image: Optional[PhotoImage] = None
        self._cached_image_id = None
        self._scale = 1.0
        self._settings = settings_service if settings_service is not None else get_settings()
        self._user_scale = self._get_user_scale()
        self._last_width = 0
        self._last_height = 0

        self._setup_ui()
        self._bind_scroll()
        self.bind("<Configure>", self._on_resize)

    def _setup_ui(self) -> None:
        sidebar_color = self._get_sidebar_color()

        self.canvas_frame = ctk.CTkFrame(
            self,
            fg_color=sidebar_color,
            corner_radius=0
        )
        self.canvas_frame.pack(fill="both", expand=True, padx=2, pady=2)
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        self.canvas = Canvas(
            self.canvas_frame,
            bg=sidebar_color,
            highlightthickness=0,
            relief="flat"
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")

        if self._landscape:
            # horizontal scrollbar for landscape orientation
            self.scrollbar = ctk.CTkScrollbar(
                self.canvas_frame,
                command=self.canvas.xview,
                orientation="horizontal",
                height=12
            )
            self.canvas.configure(xscrollcommand=self._on_scroll_set)
        else:
            # vertical scrollbar for portrait orientation
            self.scrollbar = ctk.CTkScrollbar(
                self.canvas_frame,
                command=self.canvas.yview,
                width=12
            )
            self.canvas.configure(yscrollcommand=self._on_scroll_set)
        self._scrollbar_visible = False

        self._show_placeholder()

    def _get_sidebar_color(self) -> str:
        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            return PREVIEW_SIDEBAR_COLOR_DARK
        return PREVIEW_SIDEBAR_COLOR_LIGHT

    def _bind_scroll(self) -> None:
        # add="+" prevents overwriting existing bindings on the widget
        self.canvas.bind("<Button-4>", self._on_scroll_up, add="+")
        self.canvas.bind("<Button-5>", self._on_scroll_down, add="+")
        self.canvas.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind("<Button-4>", self._on_scroll_up, add="+")
        self.bind("<Button-5>", self._on_scroll_down, add="+")
        self.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self.canvas_frame.bind("<Button-4>", self._on_scroll_up, add="+")
        self.canvas_frame.bind("<Button-5>", self._on_scroll_down, add="+")
        self.canvas_frame.bind("<MouseWheel>", self._on_mousewheel, add="+")

    def _can_scroll(self, direction: int) -> bool:
        """Check if scrolling in the given direction is allowed."""
        if self._landscape:
            left, right = self.canvas.xview()
            if left == 0.0 and right == 1.0:
                return False
            if direction < 0:
                return left > 0.0
            else:
                return right < 1.0
        else:
            top, bottom = self.canvas.yview()
            if top == 0.0 and bottom == 1.0:
                return False
            if direction < 0:
                return top > 0.0
            else:
                return bottom < 1.0

    def _on_scroll_up(self, event) -> str:
        if self._can_scroll(-1):
            if self._landscape:
                self.canvas.xview_scroll(-PREVIEW_SCROLL_UNITS, "units")
            else:
                self.canvas.yview_scroll(-PREVIEW_SCROLL_UNITS, "units")
        return "break"

    def _on_scroll_down(self, event) -> str:
        if self._can_scroll(1):
            if self._landscape:
                self.canvas.xview_scroll(PREVIEW_SCROLL_UNITS, "units")
            else:
                self.canvas.yview_scroll(PREVIEW_SCROLL_UNITS, "units")
        return "break"

    def _on_mousewheel(self, event) -> str:
        direction = -1 if event.delta > 0 else 1
        if self._can_scroll(direction):
            if self._landscape:
                self.canvas.xview_scroll(direction * PREVIEW_SCROLL_UNITS, "units")
            else:
                self.canvas.yview_scroll(direction * PREVIEW_SCROLL_UNITS, "units")
        return "break"

    def _on_scroll_set(self, first, last) -> None:
        self.scrollbar.set(first, last)
        first_f = float(first)
        last_f = float(last)
        needs_scrollbar = not (first_f <= 0 and last_f >= 1)

        if needs_scrollbar and not self._scrollbar_visible:
            if self._landscape:
                self.scrollbar.grid(row=1, column=0, sticky="ew", padx=4, pady=(4, 4))
            else:
                self.scrollbar.grid(row=0, column=1, sticky="ns", padx=(4, 4), pady=4)
            self._scrollbar_visible = True
        elif not needs_scrollbar and self._scrollbar_visible:
            self.scrollbar.grid_forget()
            self._scrollbar_visible = False

    def _get_user_scale(self) -> float:
        scale = self._settings.get(SettingsKeys.Gui.PREVIEW_SCALE, DEFAULT_PREVIEW_SCALE)
        return max(PREVIEW_MIN_SCALE, min(PREVIEW_MAX_SCALE, scale))

    def _calculate_scale(self, available_size: int) -> float:
        # refresh scale from settings
        self._user_scale = self._get_user_scale()

        paper_size = PREVIEW_PAPER_WIDTH  # paper width in portrait, paper height in landscape
        scaled_paper = paper_size * self._user_scale
        min_total = scaled_paper + (2 * PREVIEW_MIN_SIDEBAR_WIDTH)

        if available_size >= min_total:
            return self._user_scale
        else:
            usable = available_size - (2 * PREVIEW_MIN_SIDEBAR_WIDTH)
            return max(PREVIEW_MIN_SCALE, usable / paper_size)

    def _show_placeholder(self) -> None:
        self.canvas.delete("all")
        # update_idletasks removed here as it causes flashing

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width < 10:
            canvas_width = PREVIEW_FALLBACK_WIDTH
        if canvas_height < 10:
            canvas_height = PREVIEW_FALLBACK_HEIGHT

        if self._landscape:
            # landscape orientation
            self._scale = self._calculate_scale(canvas_height)
            paper_height = int(PREVIEW_PAPER_WIDTH * self._scale)
            paper_y = (canvas_height - paper_height) // 2

            self.canvas.create_rectangle(
                0, paper_y,
                canvas_width, paper_y + paper_height,
                fill="white",
                outline="gray70",
                width=PREVIEW_PAPER_BORDER_WIDTH
            )
        else:
            # portrait orientation
            self._scale = self._calculate_scale(canvas_width)
            paper_width = int(PREVIEW_PAPER_WIDTH * self._scale)
            paper_x = (canvas_width - paper_width) // 2

            self.canvas.create_rectangle(
                paper_x, 0,
                paper_x + paper_width, canvas_height,
                fill="white",
                outline="gray70",
                width=PREVIEW_PAPER_BORDER_WIDTH
            )

        self.canvas.create_text(
            canvas_width // 2,
            canvas_height // 2,
            text=PREVIEW_PLACEHOLDER_TEXT,
            fill=PREVIEW_PLACEHOLDER_COLOR,
            font=(PREVIEW_PLACEHOLDER_FONT, PREVIEW_PLACEHOLDER_FONT_SIZE)
        )

        self.canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))

    def _on_resize(self, event=None) -> None:
        # skip redraw if size unchanged to prevent flash during text input
        new_width = self.winfo_width()
        new_height = self.winfo_height()
        if new_width == self._last_width and new_height == self._last_height:
            return  # no actual size change, skip redraw
        self._last_width = new_width
        self._last_height = new_height

        # debounce rapid configure events
        if hasattr(self, '_resize_after_id'):
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(50, self._do_resize)

    def _do_resize(self) -> None:
        sidebar_color = self._get_sidebar_color()
        self.canvas.configure(bg=sidebar_color)
        self.canvas_frame.configure(fg_color=sidebar_color)

        if self._image:
            self._draw_image()
        else:
            self._show_placeholder()

    def _draw_image(self) -> None:
        if not self._image:
            return

        # get dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width < 10 or canvas_height < 10:
            return

        img_width, img_height = self._image.size

        if self._landscape:
            # landscape orientation
            self._scale = self._calculate_scale(canvas_height)
            paper_height = int(PREVIEW_PAPER_WIDTH * self._scale)
            paper_y = (canvas_height - paper_height) // 2

            display_width = int(img_width * self._scale)
            display_height = int(img_height * self._scale)

            total_width = max(canvas_width, display_width)

            self.canvas.delete("all")

            self.canvas.create_rectangle(
                0, paper_y,
                total_width, paper_y + paper_height,
                fill="white",
                outline="gray70",
                width=PREVIEW_PAPER_BORDER_WIDTH
            )

            display_image = self._image
            if display_width != img_width or display_height != img_height:
                display_image = self._image.resize(
                    (max(1, display_width), max(1, display_height)),
                    Image.Resampling.LANCZOS
                )

            if display_image.mode == '1':
                display_image = display_image.convert('RGB')
            elif display_image.mode == 'L':
                display_image = display_image.convert('RGB')

            # cache check before creating new photoimage
            current_id = (id(self._image), hash(self._image.tobytes()), display_width, display_height)
            if current_id != self._cached_image_id or self._photo_image is None:
                if is_imagetk_available():
                    self._photo_image = PhotoImage(display_image)
                    self._cached_image_id = current_id

            if self._photo_image and is_imagetk_available():
                self.canvas.create_image(
                    0,
                    paper_y,
                    anchor="nw",
                    image=self._photo_image
                )

            self.canvas.configure(scrollregion=(0, 0, total_width, canvas_height))
        else:
            # portrait orientation
            self._scale = self._calculate_scale(canvas_width)
            paper_width = int(PREVIEW_PAPER_WIDTH * self._scale)
            paper_x = (canvas_width - paper_width) // 2

            display_width = int(img_width * self._scale)
            display_height = int(img_height * self._scale)

            total_height = max(canvas_height, display_height)

            self.canvas.delete("all")

            self.canvas.create_rectangle(
                paper_x, 0,
                paper_x + paper_width, total_height,
                fill="white",
                outline="gray70",
                width=PREVIEW_PAPER_BORDER_WIDTH
            )

            display_image = self._image
            if display_width != img_width or display_height != img_height:
                display_image = self._image.resize(
                    (max(1, display_width), max(1, display_height)),
                    Image.Resampling.LANCZOS
                )

            if display_image.mode == '1':
                display_image = display_image.convert('RGB')
            elif display_image.mode == 'L':
                display_image = display_image.convert('RGB')

            # cache check before creating new photoimage
            current_id = (id(self._image), hash(self._image.tobytes()), display_width, display_height)
            if current_id != self._cached_image_id or self._photo_image is None:
                if is_imagetk_available():
                    self._photo_image = PhotoImage(display_image)
                    self._cached_image_id = current_id

            if self._photo_image and is_imagetk_available():
                self.canvas.create_image(
                    paper_x,
                    0,
                    anchor="nw",
                    image=self._photo_image
                )

            self.canvas.configure(scrollregion=(0, 0, canvas_width, total_height))

    def set_image(self, image: Optional[Image.Image]) -> None:
        if image is None:
            self._image = None
            self._photo_image = None
            self._cached_image_id = None
            self._show_placeholder()
            return

        self._image = image
        self._draw_image()

    def clear(self) -> None:
        self.set_image(None)

    def get_image(self) -> Optional[Image.Image]:
        return self._image
