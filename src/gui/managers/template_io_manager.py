"""template io manager for handling file operations"""

from typing import Optional, Callable, List
from dataclasses import dataclass
from PIL import Image
import json
import os

from ...processing.label_renderer import TextAreaConfig


@dataclass
class LabelConfig:
    template_path: Optional[str]
    template_image: Optional[Image.Image]
    text_areas: List[TextAreaConfig]
    darkness: float
    thumbnail_path: Optional[str] = None


class TemplateIOManager:
    # manages template and pcfg file operations
    # handles loading template images and saving pcfg files with thumbnails
    # generated templates like calendars have no file path until first save

    def __init__(
        self,
        on_status: Optional[Callable[[str], None]] = None,
        on_template_loaded: Optional[Callable[[Image.Image, str], None]] = None,
        save_dir: str = "gallery/templates",
    ):
        self._on_status = on_status
        self._on_template_loaded = on_template_loaded
        self._save_dir = save_dir
        self._template_path: Optional[str] = None
        self._template_image: Optional[Image.Image] = None

    @property
    def template_path(self) -> Optional[str]:
        return self._template_path

    @property
    def template_image(self) -> Optional[Image.Image]:
        return self._template_image

    def load_template(self, filepath: str) -> Optional[Image.Image]:
        try:
            image = Image.open(filepath)
            self._template_image = image
            self._template_path = filepath

            filename = os.path.basename(filepath)
            self._notify_status(f"Loaded template: {filename}")

            if self._on_template_loaded:
                self._on_template_loaded(image, filename)

            return image
        except Exception as e:
            self._notify_status(f"Error loading template: {e}")
            self._template_image = None
            self._template_path = None
            return None

    def load_pcfg(self, filepath: str) -> Optional[LabelConfig]:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # load template image if path exists
            template_path = config.get('template_path', '')
            template_image = None

            if template_path and os.path.isfile(template_path):
                template_image = self.load_template(template_path)
                if template_image is None:
                    self._notify_status("Warning: Could not load template image")
            else:
                self._notify_status("Warning: Template image not found")

            # load text areas
            text_areas_data = config.get('text_areas', [])
            text_areas = [
                TextAreaConfig.from_dict(ta) for ta in text_areas_data
            ]

            # load darkness setting
            darkness = config.get('darkness', 1.5)
            thumbnail_path = config.get('thumbnail_path')

            self._notify_status(f"Loaded: {os.path.basename(filepath)}")

            return LabelConfig(
                template_path=template_path,
                template_image=template_image,
                text_areas=text_areas,
                darkness=darkness,
                thumbnail_path=thumbnail_path,
            )
        except Exception as e:
            self._notify_status(f"Error loading config: {e}")
            return None

    def save_label(
        self,
        filepath: str,
        text_areas: List[TextAreaConfig],
        darkness: float,
        rendered_preview: Optional[Image.Image] = None,
    ) -> bool:
        try:
            os.makedirs(self._save_dir, exist_ok=True)

            # save thumbnail of rendered preview in thumbs subdirectory
            thumbnail_path = None
            if rendered_preview:
                thumbnail_path = self._save_thumbnail(filepath, rendered_preview)

            # save generated images that have no file path
            template_path_to_save = self._template_path or ""
            if not self._template_path and self._template_image:
                template_path_to_save = self._save_template_image(filepath)

            config = {
                "type": "label",
                "template_path": template_path_to_save,
                "text_areas": [ta.to_dict() for ta in text_areas],
                "darkness": darkness,
                "thumbnail_path": thumbnail_path,
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)

            self._notify_status(f"Saved: {os.path.basename(filepath)}")
            return True
        except Exception as e:
            self._notify_status(f"Error saving label: {e}")
            return False

    def set_template_image(self, image: Image.Image, name: str = "Generated") -> None:
        # for generated templates like calendar - no file path until saved
        self._template_image = image
        self._template_path = None

        self._notify_status(f"Generated: {name}")

        if self._on_template_loaded:
            self._on_template_loaded(image, name)

    def clear_template(self) -> None:
        self._template_image = None
        self._template_path = None
        self._notify_status("Template cleared")

    def _save_thumbnail(self, filepath: str, image: Image.Image, size: int = 200) -> Optional[str]:
        try:
            thumbs_dir = os.path.join(self._save_dir, "thumbs")
            os.makedirs(thumbs_dir, exist_ok=True)

            base_name = os.path.splitext(os.path.basename(filepath))[0]
            thumbnail_path = os.path.join(thumbs_dir, f"{base_name}_thumb.png")

            # maintain aspect ratio
            width, height = image.size
            if width > height:
                new_width = size
                new_height = int(height * (size / width))
            else:
                new_height = size
                new_width = int(width * (size / height))

            thumbnail = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            thumbnail.save(thumbnail_path, "PNG")

            return thumbnail_path
        except Exception as e:
            self._notify_status(f"Warning: Could not save thumbnail: {e}")
            return None

    def _save_template_image(self, filepath: str) -> str:
        # save generated template to images subdirectory
        images_dir = os.path.join(self._save_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(filepath))[0]
        template_save_path = os.path.join(images_dir, f"{base_name}_template.png")

        if self._template_image:
            self._template_image.save(template_save_path, "PNG")

        return template_save_path

    def _notify_status(self, message: str) -> None:
        if self._on_status:
            self._on_status(message)
