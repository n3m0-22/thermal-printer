"""canvas state management and coordinate transformation utilities

provides CanvasState dataclass, CoordinateTransformer, DragHandler, and CanvasRenderer
for managing interactive canvas operations with text areas on template images
"""

from dataclasses import dataclass, field
from typing import Optional, List, Callable, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

from ...processing.label_renderer import TextAreaConfig
from ...utils.font_manager import get_font_manager
from ...utils.unicode_text_renderer import get_unicode_renderer


# minimum size for empty text areas in pixels
AREA_MIN_SIZE = 60

# visual feedback colors
AREA_BORDER_NORMAL = "#666666"
AREA_BORDER_HOVER = "#4488FF"
AREA_BORDER_SELECTED = "#0066CC"
AREA_FILL_NORMAL = "#DDDDDD"
AREA_FILL_SELECTED = "#CCE5FF"
AREA_BORDER_WIDTH = 2


@dataclass
class CanvasState:
    """state container for interactive canvas with image, text areas, and drag tracking"""
    # image state
    image: Optional[Image.Image] = None
    scale: float = 1.0
    image_scale: float = 1.0
    paper_x: int = 0
    user_scale: float = 1.0

    # text areas
    text_areas: List[TextAreaConfig] = field(default_factory=list)
    selected_index: int = -1
    hovered_index: int = -1
    darkness: float = 1.5

    # copy paste
    copied_area: Optional[TextAreaConfig] = None
    last_click_x: int = 0
    last_click_y: int = 0

    # drag state
    dragging: bool = False
    drag_start_x: int = 0
    drag_start_y: int = 0
    drag_area_start_x: int = 0
    drag_area_start_y: int = 0

    # redraw scheduling
    redraw_scheduled: bool = False
    last_width: int = 0
    last_height: int = 0


class CoordinateTransformer:
    """coordinate transformations between canvas space (scaled display with sidebar)
    and template space (original image coordinates)

    accounts for paper_x offset, scale factor user zoom, and image_scale for oversized images
    """

    def __init__(self, state: CanvasState):
        self._state = state

    def canvas_to_template(self, canvas_x: int, canvas_y: int) -> tuple[int, int]:
        combined_scale = self._state.scale * self._state.image_scale
        if combined_scale == 0:
            return (0, 0)

        # remove paper offset and scale down to template space
        template_x = int((canvas_x - self._state.paper_x) / combined_scale)
        template_y = int(canvas_y / combined_scale)

        return (template_x, template_y)

    def template_to_canvas(self, template_x: int, template_y: int) -> tuple[int, int]:
        combined_scale = self._state.scale * self._state.image_scale

        # scale up from template space and add paper offset
        canvas_x = int(template_x * combined_scale) + self._state.paper_x
        canvas_y = int(template_y * combined_scale)

        return (canvas_x, canvas_y)

    def scale_dimension(self, dimension: int) -> int:
        combined_scale = self._state.scale * self._state.image_scale
        return int(dimension * combined_scale)

    def unscale_dimension(self, dimension: int) -> int:
        combined_scale = self._state.scale * self._state.image_scale
        if combined_scale == 0:
            return 0
        return int(dimension / combined_scale)


class DragHandler:
    """drag and drop operations for text areas with hit testing, position tracking,
    and callbacks for selection and movement events
    """

    def __init__(
        self,
        state: CanvasState,
        transformer: CoordinateTransformer,
        on_area_selected: Optional[Callable[[int], None]] = None,
        on_area_moved: Optional[Callable[[int, int, int], None]] = None,
    ):
        self._state = state
        self._transformer = transformer
        self._on_area_selected = on_area_selected
        self._on_area_moved = on_area_moved

    def _get_text_area_bounds(self, area: TextAreaConfig) -> Tuple[int, int, int, int]:
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

    def hit_test(self, canvas_x: int, canvas_y: int) -> int:
        template_x, template_y = self._transformer.canvas_to_template(canvas_x, canvas_y)

        for i, area in enumerate(self._state.text_areas):
            x1, y1, x2, y2 = self._get_text_area_bounds(area)
            if x1 <= template_x <= x2 and y1 <= template_y <= y2:
                return i

        return -1

    def start_drag(self, canvas_x: int, canvas_y: int) -> bool:
        hit_index = self.hit_test(canvas_x, canvas_y)

        if hit_index >= 0:
            # start dragging the hit area
            self._state.dragging = True
            self._state.selected_index = hit_index
            self._state.drag_start_x = canvas_x
            self._state.drag_start_y = canvas_y

            area = self._state.text_areas[hit_index]
            self._state.drag_area_start_x = area.x
            self._state.drag_area_start_y = area.y

            if self._on_area_selected:
                self._on_area_selected(hit_index)

            return True
        else:
            # clicked empty area - deselect
            old_selected = self._state.selected_index
            self._state.selected_index = -1
            if old_selected >= 0 and self._on_area_selected:
                self._on_area_selected(-1)
            return False

    def update_drag(self, canvas_x: int, canvas_y: int) -> Optional[Tuple[int, int]]:
        if not self._state.dragging or self._state.selected_index < 0:
            return None

        # use scale directly not combined scale for delta calculation to match original behavior
        delta_x = (canvas_x - self._state.drag_start_x) / self._state.scale
        delta_y = (canvas_y - self._state.drag_start_y) / self._state.scale

        new_x = int(self._state.drag_area_start_x + delta_x)
        new_y = int(self._state.drag_area_start_y + delta_y)

        # clamp to template bounds
        if self._state.image:
            new_x = max(0, min(new_x, self._state.image.width - 10))
            new_y = max(0, min(new_y, self._state.image.height - 10))

        # update area position
        self._state.text_areas[self._state.selected_index].x = new_x
        self._state.text_areas[self._state.selected_index].y = new_y

        return new_x, new_y

    def end_drag(self) -> Optional[Tuple[int, int, int]]:
        if not self._state.dragging or self._state.selected_index < 0:
            self._state.dragging = False
            return None

        area = self._state.text_areas[self._state.selected_index]
        result = (self._state.selected_index, area.x, area.y)

        if self._on_area_moved:
            self._on_area_moved(self._state.selected_index, area.x, area.y)

        self._state.dragging = False

        return result

    def handle_click(self, canvas_x: int, canvas_y: int) -> int:
        # track last click position for paste operations
        template_x, template_y = self._transformer.canvas_to_template(canvas_x, canvas_y)
        self._state.last_click_x = template_x
        self._state.last_click_y = template_y

        # start drag operation (which also handles selection)
        self.start_drag(canvas_x, canvas_y)

        return self._state.selected_index

    def is_dragging(self) -> bool:
        return self._state.dragging

    def get_drag_index(self) -> int:
        return self._state.selected_index if self._state.dragging else -1


class CanvasRenderer:
    """renders template images with text overlays, darkness adjustment, and visual selection indicators

    rendering done in template space then scaled for display
    """

    def __init__(self, state: CanvasState, transformer: CoordinateTransformer):
        self._state = state
        self._transformer = transformer
        self._font_manager = get_font_manager()
        self._unicode_renderer = get_unicode_renderer()

    def render_preview(self) -> Optional[Image.Image]:
        if not self._state.image:
            return None

        result = self._state.image.copy()
        if result.mode != 'RGB':
            result = result.convert('RGB')

        # scale oversized images to fit within paper width
        if self._state.image_scale < 1.0:
            new_width = int(result.width * self._state.image_scale)
            new_height = int(result.height * self._state.image_scale)
            result = result.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # render text areas onto the image
        result = self._render_text_areas(result)

        # apply darkness adjustment (contrast) to entire image
        if self._state.darkness > 1.0:
            result = self._apply_darkness(result, self._state.darkness)

        return result

    def _apply_darkness(self, image: Image.Image, darkness: float) -> Image.Image:
        if darkness <= 1.0:
            return image

        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(darkness)

    def _render_text_areas(self, image: Image.Image) -> Image.Image:
        draw = ImageDraw.Draw(image)

        for area in self._state.text_areas:
            if not area.text or not area.text.strip():
                continue

            # scale font size and positions for oversized images
            scaled_font_size = int(area.font_size * self._state.image_scale) if self._state.image_scale < 1.0 else area.font_size
            scaled_font_size = max(8, scaled_font_size)  # minimum readable size

            try:
                font = self._font_manager.load_font(
                    family=area.font_family,
                    size=scaled_font_size,
                    bold=area.bold,
                    italic=area.italic,
                )
            except Exception:
                font = ImageFont.load_default()

            # scale positions for oversized images
            scaled_y = int(area.y * self._state.image_scale) if self._state.image_scale < 1.0 else area.y
            scaled_x = int(area.x * self._state.image_scale) if self._state.image_scale < 1.0 else area.x

            # use unicode renderer for full unicode support with font fallback
            # simulate thermal printing boldness by drawing text twice with slight offset
            if self._state.darkness >= 1.3:
                # draw shadow pass for thermal print simulation
                self._unicode_renderer.draw_text_multiline(
                    draw=draw,
                    position=(scaled_x + 1, scaled_y),
                    text=area.text,
                    font=font,
                    fill=(0, 0, 0),
                    size=scaled_font_size,
                    line_spacing=1.2,
                    alignment=area.alignment
                )

            # draw main text
            self._unicode_renderer.draw_text_multiline(
                draw=draw,
                position=(scaled_x, scaled_y),
                text=area.text,
                font=font,
                fill=(0, 0, 0),
                size=scaled_font_size,
                line_spacing=1.2,
                alignment=area.alignment
            )

        return image

    def get_text_area_bounds(self, area: TextAreaConfig) -> Tuple[int, int, int, int]:
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

    def draw_selection_boxes(self, canvas, scale: float) -> None:
        for i, area in enumerate(self._state.text_areas):
            x1, y1, x2, y2 = self.get_text_area_bounds(area)

            # convert to canvas coordinates
            cx1, cy1 = self._transformer.template_to_canvas(x1, y1)
            cx2, cy2 = self._transformer.template_to_canvas(x2, y2)

            # determine colors based on state
            if i == self._state.selected_index:
                border_color = AREA_BORDER_SELECTED
                border_width = AREA_BORDER_WIDTH + 1
                dash = None
            elif i == self._state.hovered_index:
                border_color = AREA_BORDER_HOVER
                border_width = AREA_BORDER_WIDTH
                dash = None
            else:
                # normal state - dashed outline
                border_color = AREA_BORDER_NORMAL
                border_width = AREA_BORDER_WIDTH
                dash = (4, 4)

            # draw outline only - no fill
            canvas.create_rectangle(
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
            temp_id = canvas.create_text(
                cx1 + 2, label_y,
                text=label_text,
                fill=border_color,
                font=("Arial", 10, "bold"),
                anchor="nw",
                tags=f"area_label_{i}"
            )

            # add background behind label
            bbox = canvas.bbox(temp_id)
            if bbox:
                canvas.create_rectangle(
                    bbox[0] - 2, bbox[1] - 1,
                    bbox[2] + 2, bbox[3] + 1,
                    fill="white",
                    outline="",
                    tags=f"area_label_bg_{i}"
                )
                canvas.tag_raise(temp_id)
