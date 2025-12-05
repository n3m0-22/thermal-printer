# label renderer for compositing text onto template images

from typing import Optional, List
from dataclasses import dataclass, field
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import uuid

from ..config.defaults import (
    DEFAULT_FONT_SIZE,
    DEFAULT_FONT_FAMILY,
    DEFAULT_TEXT_ALIGN,
    DEFAULT_PRINTER_WIDTH,
)
from ..utils.font_manager import get_font_manager
from ..utils.unicode_text_renderer import get_unicode_renderer


@dataclass
class TextAreaConfig:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Text"
    x: int = 0
    y: int = 0
    text: str = ""
    font_family: str = DEFAULT_FONT_FAMILY
    font_size: int = DEFAULT_FONT_SIZE
    bold: bool = False
    italic: bool = False
    alignment: str = DEFAULT_TEXT_ALIGN

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "text": self.text,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "bold": self.bold,
            "italic": self.italic,
            "alignment": self.alignment,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TextAreaConfig":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Text"),
            x=data.get("x", 0),
            y=data.get("y", 0),
            text=data.get("text", ""),
            font_family=data.get("font_family", DEFAULT_FONT_FAMILY),
            font_size=data.get("font_size", DEFAULT_FONT_SIZE),
            bold=data.get("bold", False),
            italic=data.get("italic", False),
            alignment=data.get("alignment", DEFAULT_TEXT_ALIGN),
        )


@dataclass
class LabelConfig:
    template_path: str = ""
    text_areas: List[TextAreaConfig] = field(default_factory=list)
    darkness: float = 1.5

    def to_dict(self) -> dict:
        return {
            "template_path": self.template_path,
            "text_areas": [ta.to_dict() for ta in self.text_areas],
            "darkness": self.darkness,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LabelConfig":
        text_areas = [
            TextAreaConfig.from_dict(ta)
            for ta in data.get("text_areas", [])
        ]
        return cls(
            template_path=data.get("template_path", ""),
            text_areas=text_areas,
            darkness=data.get("darkness", 1.5),
        )


class LabelRenderer:
    def __init__(
        self,
        template: Optional[Image.Image] = None,
        target_width: int = DEFAULT_PRINTER_WIDTH,
    ):
        self._template: Optional[Image.Image] = template
        self._target_width = target_width
        self._font_manager = get_font_manager()
        self._unicode_renderer = get_unicode_renderer()

    def set_template(self, template: Optional[Image.Image]) -> None:
        self._template = template

    def get_template(self) -> Optional[Image.Image]:
        return self._template

    def get_template_size(self) -> tuple:
        if self._template:
            return self._template.size
        return (0, 0)

    def _load_font(self, config: TextAreaConfig) -> ImageFont.FreeTypeFont:
        return self._font_manager.load_font(
            family=config.font_family,
            size=config.font_size,
            bold=config.bold,
            italic=config.italic,
        )

    def _render_text_area(
        self,
        draw: ImageDraw.ImageDraw,
        config: TextAreaConfig,
    ) -> None:
        if not config.text.strip():
            return

        font = self._load_font(config)

        # unicode renderer provides automatic font fallback for emoji and symbols
        self._unicode_renderer.draw_text_multiline(
            draw=draw,
            position=(config.x, config.y),
            text=config.text,
            font=font,
            fill=(0, 0, 0),
            size=config.font_size,
            line_spacing=1.2,
            alignment=config.alignment
        )

    def render(
        self,
        text_areas: List[TextAreaConfig],
        darkness: float = 1.5,
    ) -> Optional[Image.Image]:
        if not self._template:
            return None

        result = self._template.copy()
        if result.mode != 'RGB':
            result = result.convert('RGB')

        draw = ImageDraw.Draw(result)

        for config in text_areas:
            self._render_text_area(draw, config)

        if darkness != 1.0:
            enhancer = ImageEnhance.Contrast(result)
            result = enhancer.enhance(darkness)

        return result

    def get_preview(
        self,
        text_areas: List[TextAreaConfig],
        darkness: float = 1.5,
    ) -> Optional[Image.Image]:
        return self.render(text_areas, darkness)

    def get_print_image(
        self,
        text_areas: List[TextAreaConfig],
        darkness: float = 1.5,
    ) -> Optional[Image.Image]:
        result = self.render(text_areas, darkness)
        if not result:
            return None

        if result.width != self._target_width:
            scale = self._target_width / result.width
            new_height = int(result.height * scale)
            result = result.resize(
                (self._target_width, new_height),
                Image.Resampling.LANCZOS
            )

        return result
