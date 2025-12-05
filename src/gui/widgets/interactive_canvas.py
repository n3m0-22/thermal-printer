# interactive canvas for drag and drop text area positioning on labels
#
# this canvas displays a scaled preview of the template image and allows users
# to drag text areas to new positions
# coordinate transforms are needed between canvas space and template space
# the _canvas_to_template and _template_to_canvas methods handle this conversion
# the _paper_x offset accounts for the gray sidebar that simulates paper edges

from typing import Optional, Callable, List, Tuple, TYPE_CHECKING
import customtkinter as ctk
from tkinter import Canvas
from dataclasses import replace
from ...utils.pil_compat import Image, ImageDraw, ImageFont, ImageEnhance, PhotoImage, is_imagetk_available

if TYPE_CHECKING:
    from ...interfaces import SettingsService

from ...config.defaults import (
    PREVIEW_PAPER_WIDTH,
    PREVIEW_MIN_SIDEBAR_WIDTH,
    PREVIEW_PAPER_BORDER_WIDTH,
    PREVIEW_SIDEBAR_COLOR_LIGHT,
    PREVIEW_SIDEBAR_COLOR_DARK,
    PREVIEW_MIN_SCALE,
    PREVIEW_MAX_SCALE,
    DEFAULT_PREVIEW_SCALE,
    PREVIEW_FALLBACK_WIDTH,
    PREVIEW_FALLBACK_HEIGHT,
    PREVIEW_SCROLL_UNITS,
    CANVAS_AREA_BORDER_NORMAL,
    CANVAS_AREA_BORDER_HOVER,
    CANVAS_AREA_BORDER_SELECTED,
    CANVAS_AREA_BORDER_WIDTH,
    CANVAS_DARKNESS_BOLD_THRESHOLD,
    CANVAS_LABEL_BG_COLOR,
)
from ...config.settings import get_settings
from ...config.keys import SettingsKeys
from ...processing.label_renderer import TextAreaConfig
from ...utils.font_manager import get_font_manager
from ...utils.unicode_text_renderer import get_unicode_renderer


# minimum size for empty text areas
AREA_MIN_SIZE = 60


class InteractiveCanvas(ctk.CTkFrame):
    # canvas with drag-and-drop support for positioning text areas

    def __init__(
        self,
        master,
        on_area_selected: Optional[Callable[[int], None]] = None,
        on_area_moved: Optional[Callable[[int, int, int], None]] = None,
        on_area_added: Optional[Callable[[TextAreaConfig], None]] = None,
        min_height: int = 150,
        settings_service: Optional["SettingsService"] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)

        self.on_area_selected = on_area_selected
        self.on_area_moved = on_area_moved
        self.on_area_added = on_area_added
        self.min_height = min_height

        self._image: Optional[Image.Image] = None
        self._photo_image: Optional[PhotoImage] = None
        self._scale = 1.0
        self._image_scale = 1.0  # additional scaling for oversized images
        self._paper_x = 0
        self._settings = settings_service if settings_service else get_settings()
        self._user_scale = self._get_user_scale()

        # text areas state
        self._text_areas: List[TextAreaConfig] = []
        self._selected_index: int = -1
        self._hovered_index: int = -1
        self._darkness: float = 1.5  # match default print darkness

        # copy/paste state
        self._copied_area: Optional[TextAreaConfig] = None
        self._last_click_x: int = 0
        self._last_click_y: int = 0

        # drag state
        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_area_start_x = 0
        self._drag_area_start_y = 0

        # redraw scheduling
        self._redraw_scheduled = False
        self._tooltip_id = None
        self._last_width = 0
        self._last_height = 0

        self._setup_ui()
        self._bind_events()

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
            relief="flat",
            cursor="arrow"
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # vertical scrollbar for portrait orientation only
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

    def _bind_events(self) -> None:
        # add="+" prevents overwriting existing bindings
        self.canvas.bind("<Button-4>", self._on_scroll_up, add="+")
        self.canvas.bind("<Button-5>", self._on_scroll_down, add="+")
        self.canvas.bind("<MouseWheel>", self._on_mousewheel, add="+")

        # click and drag bindings
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)

        # keyboard bindings for copy/paste
        self.canvas.bind("<Control-c>", self._on_copy)
        self.canvas.bind("<Control-v>", self._on_paste)

        # make canvas focusable for keyboard events
        self.canvas.bind("<Button-1>", self._focus_canvas, add="+")

        # resize binding
        self.bind("<Configure>", self._on_resize)

    def _can_scroll(self, direction: int) -> bool:
        """Check if scrolling in the given direction is allowed."""
        top, bottom = self.canvas.yview()
        if top == 0.0 and bottom == 1.0:
            return False
        if direction < 0:
            return top > 0.0
        else:
            return bottom < 1.0

    def _on_scroll_up(self, event) -> str:
        if self._can_scroll(-1):
            self.canvas.yview_scroll(-PREVIEW_SCROLL_UNITS, "units")
        return "break"

    def _on_scroll_down(self, event) -> str:
        if self._can_scroll(1):
            self.canvas.yview_scroll(PREVIEW_SCROLL_UNITS, "units")
        return "break"

    def _on_mousewheel(self, event) -> str:
        direction = -1 if event.delta > 0 else 1
        if self._can_scroll(direction):
            self.canvas.yview_scroll(direction * PREVIEW_SCROLL_UNITS, "units")
        return "break"

    def _on_scroll_set(self, first, last) -> None:
        self.scrollbar.set(first, last)
        first_f = float(first)
        last_f = float(last)
        needs_scrollbar = not (first_f <= 0 and last_f >= 1)

        if needs_scrollbar and not self._scrollbar_visible:
            self.scrollbar.grid(row=0, column=1, sticky="ns", padx=(4, 4), pady=4)
            self._scrollbar_visible = True
        elif not needs_scrollbar and self._scrollbar_visible:
            self.scrollbar.grid_forget()
            self._scrollbar_visible = False

    def _get_user_scale(self) -> float:
        scale = self._settings.get(SettingsKeys.Gui.PREVIEW_SCALE, DEFAULT_PREVIEW_SCALE)
        return max(PREVIEW_MIN_SCALE, min(PREVIEW_MAX_SCALE, scale))

    def _calculate_scale(self, available_width: int) -> float:
        # refresh user scale from settings
        self._user_scale = self._get_user_scale()

        paper_width = PREVIEW_PAPER_WIDTH
        scaled_paper = paper_width * self._user_scale
        min_total = scaled_paper + (2 * PREVIEW_MIN_SIDEBAR_WIDTH)

        if available_width >= min_total:
            return self._user_scale
        else:
            usable = available_width - (2 * PREVIEW_MIN_SIDEBAR_WIDTH)
            return max(PREVIEW_MIN_SCALE, usable / paper_width)

    def _canvas_to_template(self, canvas_x: int, canvas_y: int) -> Tuple[int, int]:
        # convert canvas coordinates to template coordinates
        combined_scale = self._scale * self._image_scale
        if combined_scale == 0:
            return 0, 0
        template_x = int((canvas_x - self._paper_x) / combined_scale)
        template_y = int(canvas_y / combined_scale)
        return template_x, template_y

    def _template_to_canvas(self, template_x: int, template_y: int) -> Tuple[int, int]:
        # convert template coordinates to canvas coordinates
        combined_scale = self._scale * self._image_scale
        canvas_x = int(template_x * combined_scale) + self._paper_x
        canvas_y = int(template_y * combined_scale)
        return canvas_x, canvas_y

    def _get_area_bounds(self, area: TextAreaConfig) -> Tuple[int, int, int, int]:
        # calculate text area bounds for hit testing and display
        # returns (x1, y1, x2, y2) in template coordinates
        font_height = int(area.font_size * 1.2)

        # calculate size based on text content, with minimum size
        if area.text and area.text.strip():
            text_lines = area.text.split('\n')
            max_chars = max(len(line) for line in text_lines) if text_lines else 0
            num_lines = len(text_lines)
            est_width = max(int(max_chars * area.font_size * 0.6), AREA_MIN_SIZE)
            est_height = max(num_lines * font_height, font_height)
        else:
            # minimum visible size for empty text areas
            est_width = AREA_MIN_SIZE
            est_height = font_height

        x1 = area.x
        y1 = area.y

        # adjust x1 based on alignment
        if area.alignment == "center":
            x1 = area.x - est_width // 2
        elif area.alignment == "right":
            x1 = area.x - est_width

        x2 = x1 + est_width
        y2 = y1 + est_height

        return int(x1), int(y1), int(x2), int(y2)

    def _hit_test(self, canvas_x: int, canvas_y: int) -> int:
        # return index of text area at canvas position, or -1
        template_x, template_y = self._canvas_to_template(canvas_x, canvas_y)

        for i, area in enumerate(self._text_areas):
            x1, y1, x2, y2 = self._get_area_bounds(area)
            if x1 <= template_x <= x2 and y1 <= template_y <= y2:
                return i

        return -1

    def _focus_canvas(self, event) -> None:
        # give canvas focus for keyboard events
        self.canvas.focus_set()

    def _on_click(self, event) -> None:
        # get canvas coordinates accounting for scroll
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        # track last click position for paste
        template_x, template_y = self._canvas_to_template(canvas_x, canvas_y)
        self._last_click_x = template_x
        self._last_click_y = template_y

        hit_index = self._hit_test(canvas_x, canvas_y)

        if hit_index >= 0:
            self._selected_index = hit_index
            self._dragging = True
            self._drag_start_x = canvas_x
            self._drag_start_y = canvas_y

            area = self._text_areas[hit_index]
            self._drag_area_start_x = area.x
            self._drag_area_start_y = area.y

            self.canvas.configure(cursor="fleur")

            if self.on_area_selected:
                self.on_area_selected(hit_index)
        else:
            # clicked empty area - deselect but keep showing indicators
            old_selected = self._selected_index
            self._selected_index = -1
            if old_selected >= 0 and self.on_area_selected:
                self.on_area_selected(-1)

        self._schedule_redraw()

    def _on_drag(self, event) -> None:
        if not self._dragging or self._selected_index < 0:
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        # calculate delta in template coordinates
        # uses scale not combined_scale to preserve expected drag behavior
        delta_x = (canvas_x - self._drag_start_x) / self._scale
        delta_y = (canvas_y - self._drag_start_y) / self._scale

        new_x = int(self._drag_area_start_x + delta_x)
        new_y = int(self._drag_area_start_y + delta_y)

        # clamp to template bounds
        if self._image:
            new_x = max(0, min(new_x, self._image.width - 10))
            new_y = max(0, min(new_y, self._image.height - 10))

        # update area position
        self._text_areas[self._selected_index].x = new_x
        self._text_areas[self._selected_index].y = new_y

        # fast indicator-only redraw during drag - no full image redraw needed
        self._redraw_indicators_only()
        self._show_tooltip(event.x, event.y, new_x, new_y)

    def _on_release(self, event) -> None:
        if self._dragging and self._selected_index >= 0:
            area = self._text_areas[self._selected_index]
            if self.on_area_moved:
                self.on_area_moved(self._selected_index, area.x, area.y)

        self._dragging = False
        self.canvas.configure(cursor="arrow")
        self._hide_tooltip()

    def _on_motion(self, event) -> None:
        if self._dragging:
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        hit_index = self._hit_test(canvas_x, canvas_y)

        if hit_index != self._hovered_index:
            self._hovered_index = hit_index
            if hit_index >= 0:
                self.canvas.configure(cursor="hand2")
            else:
                self.canvas.configure(cursor="arrow")
            # fast indicator-only redraw for hover - no full image redraw needed
            self._redraw_indicators_only()

    def _on_leave(self, event) -> None:
        if not self._dragging:
            self._hovered_index = -1
            self.canvas.configure(cursor="arrow")
            # fast indicator-only redraw for leave - no full image redraw needed
            self._redraw_indicators_only()
        self._hide_tooltip()

    def _on_copy(self, event=None) -> str:
        # copy selected area
        self._do_copy()
        return "break"

    def _on_paste(self, event=None) -> str:
        # paste at last click position
        self._do_paste(self._last_click_x, self._last_click_y)
        return "break"

    def _do_copy(self) -> None:
        # copy the selected area
        if self._selected_index < 0 or self._selected_index >= len(self._text_areas):
            return

        # store a copy of the selected area
        area = self._text_areas[self._selected_index]
        self._copied_area = replace(area)

    def _do_paste(self, x: int, y: int) -> None:
        # paste the copied area at the given position
        if self._copied_area is None:
            return

        # create a new area from the copied one with new position
        new_area = replace(
            self._copied_area,
            name=f"Area {len(self._text_areas) + 1}",
            x=x,
            y=y
        )

        # notify parent to add the area
        if self.on_area_added:
            self.on_area_added(new_area)

    def _show_tooltip(self, x: int, y: int, template_x: int, template_y: int) -> None:
        self._hide_tooltip()
        self._tooltip_id = self.canvas.create_text(
            x + 15, y - 15,
            text=f"({template_x}, {template_y})",
            fill="white",
            font=("Arial", 10),
            anchor="nw",
            tags="tooltip"
        )
        # background for tooltip
        bbox = self.canvas.bbox(self._tooltip_id)
        if bbox:
            self.canvas.create_rectangle(
                bbox[0] - 3, bbox[1] - 2,
                bbox[2] + 3, bbox[3] + 2,
                fill=CANVAS_LABEL_BG_COLOR,
                outline="",
                tags="tooltip_bg"
            )
            self.canvas.tag_raise(self._tooltip_id)

    def _hide_tooltip(self) -> None:
        self.canvas.delete("tooltip")
        self.canvas.delete("tooltip_bg")
        self._tooltip_id = None

    def _on_resize(self, event=None) -> None:
        # only redraw if dimensions actually changed - prevents flash on text typing
        new_width = self.winfo_width()
        new_height = self.winfo_height()
        if new_width == self._last_width and new_height == self._last_height:
            return  # no actual size change, skip redraw
        self._last_width = new_width
        self._last_height = new_height

        # debounce resize to prevent flashing from rapid Configure events
        if hasattr(self, '_resize_after_id'):
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(50, self._do_resize_update)

    def _do_resize_update(self) -> None:
        sidebar_color = self._get_sidebar_color()
        self.canvas.configure(bg=sidebar_color)
        self.canvas_frame.configure(fg_color=sidebar_color)
        self._schedule_redraw()

    def _show_placeholder(self) -> None:
        self.canvas.delete("all")
        # removed update_idletasks() - causes flashing

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width < 10:
            canvas_width = PREVIEW_FALLBACK_WIDTH
        if canvas_height < 10:
            canvas_height = PREVIEW_FALLBACK_HEIGHT

        self._scale = self._calculate_scale(canvas_width)
        paper_width = int(PREVIEW_PAPER_WIDTH * self._scale)
        self._paper_x = (canvas_width - paper_width) // 2

        self.canvas.create_rectangle(
            self._paper_x, 0,
            self._paper_x + paper_width, canvas_height,
            fill="white",
            outline="gray70",
            width=PREVIEW_PAPER_BORDER_WIDTH
        )

        self.canvas.create_text(
            canvas_width // 2,
            canvas_height // 2,
            text="Load a template to start",
            fill="gray50",
            font=("Arial", 14)
        )

        self.canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))

    def _schedule_redraw(self) -> None:
        # debounce redraws - only schedule one
        if not self._redraw_scheduled:
            self._redraw_scheduled = True
            self.after_idle(self._deferred_redraw)

    def _deferred_redraw(self) -> None:
        self._redraw_scheduled = False
        self._do_redraw()

    def _redraw_indicators_only(self) -> None:
        # fast path to redraw only indicators during drag and hover without touching the image
        if not self._image:
            return

        # delete only indicator-tagged canvas items
        for i in range(len(self._text_areas)):
            self.canvas.delete(f"area_{i}")
            self.canvas.delete(f"area_label_{i}")
            self.canvas.delete(f"area_label_bg_{i}")

        # redraw indicators on top of existing image
        self._draw_area_indicators()

    def _do_redraw(self) -> None:
        # actual redraw implementation
        if not self._image:
            self._show_placeholder()
            return

        # get dimensions without forcing immediate repaint
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # if canvas not ready, schedule for later
        if canvas_width < 10 or canvas_height < 10:
            self.after(50, self._schedule_redraw)
            return

        img_width, img_height = self._image.size

        self._scale = self._calculate_scale(canvas_width)
        paper_width = int(PREVIEW_PAPER_WIDTH * self._scale)
        self._paper_x = (canvas_width - paper_width) // 2

        # scale image to fit within paper width while maintaining aspect ratio
        if img_width > PREVIEW_PAPER_WIDTH:
            # image is wider than paper - scale down to fit
            self._image_scale = PREVIEW_PAPER_WIDTH / img_width
            display_width = int(PREVIEW_PAPER_WIDTH * self._scale)
            display_height = int(img_height * self._image_scale * self._scale)
        else:
            # image fits within paper
            self._image_scale = 1.0
            display_width = int(img_width * self._scale)
            display_height = int(img_height * self._scale)

        total_height = max(canvas_height, display_height)

        self.canvas.delete("all")

        # draw paper background
        self.canvas.create_rectangle(
            self._paper_x, 0,
            self._paper_x + paper_width, total_height,
            fill="white",
            outline="gray70",
            width=PREVIEW_PAPER_BORDER_WIDTH
        )

        # render text onto template copy for preview
        preview_image = self._render_text_on_template()

        # scale for display
        if display_width != img_width or display_height != img_height:
            preview_image = preview_image.resize(
                (max(1, display_width), max(1, display_height)),
                Image.Resampling.LANCZOS
            )

        if preview_image.mode == '1':
            preview_image = preview_image.convert('RGB')
        elif preview_image.mode == 'L':
            preview_image = preview_image.convert('RGB')

        if is_imagetk_available():
            self._photo_image = PhotoImage(preview_image)

            self.canvas.create_image(
                self._paper_x,
                0,
                anchor="nw",
                image=self._photo_image
            )

        # always draw text area indicators on top
        self._draw_area_indicators()

        self.canvas.configure(scrollregion=(0, 0, canvas_width, total_height))

    def _render_text_on_template(self) -> Image.Image:
        # render text areas onto a copy of the template for preview
        if not self._image:
            return Image.new('RGB', (100, 100), 'white')

        result = self._image.copy()
        if result.mode != 'RGB':
            result = result.convert('RGB')

        # scale oversized images to fit within paper width
        if self._image_scale < 1.0:
            new_width = int(result.width * self._image_scale)
            new_height = int(result.height * self._image_scale)
            result = result.resize((new_width, new_height), Image.Resampling.LANCZOS)

        draw = ImageDraw.Draw(result)
        font_manager = get_font_manager()
        unicode_renderer = get_unicode_renderer()

        for area in self._text_areas:
            if not area.text or not area.text.strip():
                continue

            # scale font size and positions for oversized images
            scaled_font_size = int(area.font_size * self._image_scale) if self._image_scale < 1.0 else area.font_size
            scaled_font_size = max(8, scaled_font_size)  # minimum readable size

            try:
                font = font_manager.load_font(
                    family=area.font_family,
                    size=scaled_font_size,
                    bold=area.bold,
                    italic=area.italic,
                )
            except Exception:
                font = ImageFont.load_default()

            # scale positions for oversized images
            scaled_y = int(area.y * self._image_scale) if self._image_scale < 1.0 else area.y
            scaled_x = int(area.x * self._image_scale) if self._image_scale < 1.0 else area.x

            # use unicode renderer for full unicode support with font fallback
            # simulate thermal printing boldness by drawing text twice with slight offset
            if self._darkness >= CANVAS_DARKNESS_BOLD_THRESHOLD:
                # draw shadow pass for thermal print simulation
                unicode_renderer.draw_text_multiline(
                    draw=draw,
                    position=(scaled_x + 1, scaled_y),
                    text=area.text,
                    font=font,
                    fill=(0, 0, 0),
                    size=scaled_font_size,
                    line_spacing=1.2,
                    alignment=area.alignment
                )
            unicode_renderer.draw_text_multiline(
                draw=draw,
                position=(scaled_x, scaled_y),
                text=area.text,
                font=font,
                fill=(0, 0, 0),
                size=scaled_font_size,
                line_spacing=1.2,
                alignment=area.alignment
            )

        # apply darkness adjustment (contrast) to entire image
        if self._darkness > 1.0:
            enhancer = ImageEnhance.Contrast(result)
            result = enhancer.enhance(self._darkness)

        return result

    def _draw_area_indicators(self) -> None:
        # draw visual indicators for ALL text areas - outline only, no fill
        for i, area in enumerate(self._text_areas):
            x1, y1, x2, y2 = self._get_area_bounds(area)

            # convert to canvas coordinates
            cx1, cy1 = self._template_to_canvas(x1, y1)
            cx2, cy2 = self._template_to_canvas(x2, y2)

            # determine colors based on state
            if i == self._selected_index:
                border_color = CANVAS_AREA_BORDER_SELECTED
                border_width = CANVAS_AREA_BORDER_WIDTH + 1
                dash = None
            elif i == self._hovered_index:
                border_color = CANVAS_AREA_BORDER_HOVER
                border_width = CANVAS_AREA_BORDER_WIDTH
                dash = None
            else:
                # normal state - dashed outline
                border_color = CANVAS_AREA_BORDER_NORMAL
                border_width = CANVAS_AREA_BORDER_WIDTH
                dash = (4, 4)

            # draw outline only - no fill
            self.canvas.create_rectangle(
                cx1, cy1, cx2, cy2,
                outline=border_color,
                fill="",
                width=border_width,
                dash=dash,
                tags=f"area_{i}"
            )

            # draw area name label
            label_y = cy1 - 16 if cy1 > 20 else cy2 + 4

            # label background for visibility
            label_text = area.name
            temp_id = self.canvas.create_text(
                cx1 + 2, label_y,
                text=label_text,
                fill=border_color,
                font=("Arial", 10, "bold"),
                anchor="nw",
                tags=f"area_label_{i}"
            )

            # add background behind label
            bbox = self.canvas.bbox(temp_id)
            if bbox:
                self.canvas.create_rectangle(
                    bbox[0] - 2, bbox[1] - 1,
                    bbox[2] + 2, bbox[3] + 1,
                    fill="white",
                    outline="",
                    tags=f"area_label_bg_{i}"
                )
                self.canvas.tag_raise(temp_id)

    # public api for updating all state
    def update_state(
        self,
        image: Optional[Image.Image] = None,
        text_areas: Optional[List[TextAreaConfig]] = None,
        selected_index: Optional[int] = None,
        darkness: Optional[float] = None
    ) -> None:
        if image is not None:
            self._image = image
        if text_areas is not None:
            self._text_areas = text_areas
        if selected_index is not None:
            self._selected_index = selected_index
        if darkness is not None:
            self._darkness = darkness
        self._schedule_redraw()

    def set_darkness(self, darkness: float) -> None:
        self._darkness = darkness
        self._schedule_redraw()

    def set_image(self, image: Optional[Image.Image]) -> None:
        if image is None:
            self._image = None
            self._photo_image = None
            self._show_placeholder()
            return

        self._image = image
        self._schedule_redraw()

    def set_text_areas(self, areas: List[TextAreaConfig]) -> None:
        self._text_areas = areas
        self._schedule_redraw()

    def set_selected_index(self, index: int) -> None:
        self._selected_index = index
        self._schedule_redraw()

    def clear(self) -> None:
        self._image = None
        self._photo_image = None
        self._text_areas = []
        self._selected_index = -1
        self._show_placeholder()

    def get_image(self) -> Optional[Image.Image]:
        return self._image

    def get_rendered_preview(self) -> Optional[Image.Image]:
        if not self._image:
            return None
        return self._render_text_on_template()
