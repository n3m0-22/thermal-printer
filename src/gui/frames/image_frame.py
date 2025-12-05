# image loading and processing frame for image printing

from typing import Optional, Callable, TYPE_CHECKING
import json
import os
import customtkinter as ctk
from PIL import Image

from ...config.defaults import (
    DEFAULT_BRIGHTNESS,
    DEFAULT_CONTRAST,
    DEFAULT_DITHER_MODE,
    DEFAULT_ROTATION,
    DITHER_MODES,
    ROTATION_OPTIONS,
    SUPPORTED_IMAGE_FORMATS,
)

# image downsampling constants to reduce memory usage
MAX_PREVIEW_HEIGHT = 2000  # max height for preview images
DOWNSAMPLE_THRESHOLD = 4000  # threshold above which to downsample
from ...config.keys import SettingsKeys
from ...config.settings import get_settings
from ...processing.image_processor import ImageProcessor
from ..widgets.preview_canvas import PreviewCanvas
from ...utils.file_dialogs import open_file_dialog, save_file_dialog
from ..dialogs.template_gallery import TemplateGallery

# service interfaces
if TYPE_CHECKING:
    from ..interfaces import PrinterService, StatusService, SettingsService
from ..interfaces import create_services_from_app


class ImageFrame(ctk.CTkFrame):

    def __init__(
        self,
        master,
        on_print_request: Optional[Callable] = None,
        on_status_change: Optional[Callable[[str], None]] = None,
        printer_service: Optional["PrinterService"] = None,
        status_service: Optional["StatusService"] = None,
        settings_service: Optional["SettingsService"] = None,
        app=None,  # backward compatibility - accepts full app instance
        **kwargs
    ):
        super().__init__(master, **kwargs)

        # service interfaces for dependency injection
        # if services not provided but app is then create adapters
        if app is not None and (printer_service is None or status_service is None or settings_service is None):
            _printer, _status, _settings, _conn = create_services_from_app(app)
            printer_service = printer_service or _printer
            status_service = status_service or _status
            settings_service = settings_service or _settings

        self._printer_service = printer_service
        self._status_service = status_service
        self._settings_service = settings_service

        # legacy callbacks for backward compatibility
        self.on_print_request = on_print_request
        self.on_status_change = on_status_change

        # use injected settings service or fallback to global
        self._settings = settings_service if settings_service else get_settings()
        self._source_image: Optional[Image.Image] = None
        self._source_image_path: Optional[str] = None
        self._original_image_path: Optional[str] = None  # path to full resolution image
        self._preview_image: Optional[Image.Image] = None  # downsampled image for preview
        self._processor: Optional[ImageProcessor] = None

        self._templates_dir = "gallery/images"

        self._setup_ui()
        self._load_settings()
        self._init_processor()

    def _setup_ui(self) -> None:
        label_font = ctk.CTkFont(size=14, weight="bold")
        ctrl_font = ctk.CTkFont(size=14)
        btn_font = ctk.CTkFont(size=14)
        filename_font = ctk.CTkFont(size=15)

        # buttons at bottom first so always visible
        button_wrapper = ctk.CTkFrame(self, fg_color="transparent", height=50)
        button_wrapper.pack(side="bottom", fill="x", padx=10, pady=(5, 10))
        button_wrapper.pack_propagate(False)

        button_frame = ctk.CTkFrame(button_wrapper, fg_color="transparent")
        button_frame.pack(fill="x", expand=True, pady=4)

        # brightness and contrast sliders
        adjust_frame = ctk.CTkFrame(self, fg_color="transparent")
        adjust_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(adjust_frame, text="Brightness:", font=label_font, width=85, anchor="w").pack(side="left", padx=(0, 5))

        self.brightness_var = ctk.DoubleVar(value=DEFAULT_BRIGHTNESS)
        self.brightness_slider = ctk.CTkSlider(
            adjust_frame,
            from_=0.2, to=2.0,
            variable=self.brightness_var,
            width=180, height=20,
            command=self._on_adjustment_change
        )
        self.brightness_slider.pack(side="left", padx=5)

        self.brightness_value = ctk.CTkLabel(adjust_frame, text="1.0", width=45, font=ctrl_font)
        self.brightness_value.pack(side="left", padx=(0, 25))

        ctk.CTkLabel(adjust_frame, text="Contrast:", font=label_font, width=75).pack(side="left", padx=(0, 5))

        self.contrast_var = ctk.DoubleVar(value=DEFAULT_CONTRAST)
        self.contrast_slider = ctk.CTkSlider(
            adjust_frame,
            from_=0.2, to=2.0,
            variable=self.contrast_var,
            width=180, height=20,
            command=self._on_adjustment_change
        )
        self.contrast_slider.pack(side="left", padx=5)

        self.contrast_value = ctk.CTkLabel(adjust_frame, text="1.0", width=45, font=ctrl_font)
        self.contrast_value.pack(side="left")

        # dithering rotation invert options
        options_frame = ctk.CTkFrame(self, fg_color="transparent")
        options_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(options_frame, text="Dithering:", font=label_font, width=85, anchor="w").pack(side="left", padx=(0, 5))

        self.dither_var = ctk.StringVar(value=DEFAULT_DITHER_MODE)
        self.dither_dropdown = ctk.CTkOptionMenu(
            options_frame,
            values=DITHER_MODES,
            variable=self.dither_var,
            width=160, height=32,
            font=ctrl_font,
            dynamic_resizing=False,
            command=self._on_option_change
        )
        self.dither_dropdown.pack(side="left", padx=(0, 25))

        ctk.CTkLabel(options_frame, text="Rotation:", font=label_font, width=75).pack(side="left", padx=(0, 5))

        rotation_values = [str(r) for r in ROTATION_OPTIONS]
        self.rotation_var = ctk.StringVar(value=str(DEFAULT_ROTATION))
        self.rotation_dropdown = ctk.CTkOptionMenu(
            options_frame,
            values=rotation_values,
            variable=self.rotation_var,
            width=90, height=32,
            font=ctrl_font,
            dynamic_resizing=False,
            command=self._on_option_change
        )
        self.rotation_dropdown.pack(side="left", padx=(0, 25))

        self.invert_var = ctk.BooleanVar(value=False)
        self.invert_checkbox = ctk.CTkCheckBox(
            options_frame,
            text="Invert",
            variable=self.invert_var,
            font=ctrl_font,
            command=self._on_option_change
        )
        self.invert_checkbox.pack(side="left", padx=(0, 15))

        self.show_dither_var = ctk.BooleanVar(value=False)
        self.dither_preview_check = ctk.CTkCheckBox(
            options_frame,
            text="Show dithering",
            variable=self.show_dither_var,
            font=ctrl_font,
            command=self._update_preview
        )
        self.dither_preview_check.pack(side="left", padx=(0, 15))

        # preview canvas expands to fill space
        preview_container = ctk.CTkFrame(self)
        preview_container.pack(fill="both", expand=True, padx=10, pady=5)

        self.preview_canvas = PreviewCanvas(preview_container)
        self.preview_canvas.pack(fill="both", expand=True)

        btn_width = 100
        btn_height = 36

        self.gallery_button = ctk.CTkButton(
            button_frame,
            text="Gallery",
            width=btn_width, height=btn_height,
            font=btn_font,
            command=self._on_show_gallery
        )
        self.gallery_button.pack(side="left", padx=(0, 8))

        self.clear_button = ctk.CTkButton(
            button_frame,
            text="Clear",
            width=btn_width, height=btn_height,
            font=btn_font,
            command=self._on_clear
        )
        self.clear_button.pack(side="left", padx=(0, 8))

        self.filename_label = ctk.CTkLabel(
            button_frame,
            text="No image loaded",
            text_color="gray",
            font=filename_font
        )
        self.filename_label.pack(side="left", fill="x", expand=True, padx=(8, 8))

        self.print_button = ctk.CTkButton(
            button_frame,
            text="Print",
            width=btn_width, height=btn_height,
            font=btn_font,
            fg_color=("green", "#00AA00"),
            hover_color=("darkgreen", "#008800"),
            command=self._on_print
        )
        self.print_button.pack(side="right")

        self.save_button = ctk.CTkButton(
            button_frame,
            text="Save",
            width=btn_width, height=btn_height,
            font=btn_font,
            command=self._on_save
        )
        self.save_button.pack(side="right", padx=(0, 8))

    def _load_settings(self) -> None:
        self.brightness_var.set(self._settings.get(SettingsKeys.Image.BRIGHTNESS, DEFAULT_BRIGHTNESS))
        self.contrast_var.set(self._settings.get(SettingsKeys.Image.CONTRAST, DEFAULT_CONTRAST))
        self.dither_var.set(self._settings.get(SettingsKeys.Image.DITHER_MODE, DEFAULT_DITHER_MODE))
        self.rotation_var.set(str(self._settings.get(SettingsKeys.Image.ROTATION, DEFAULT_ROTATION)))
        self.invert_var.set(self._settings.get(SettingsKeys.Image.INVERT, False))

        self._update_value_labels()

    def _save_settings(self) -> None:
        self._settings.set(SettingsKeys.Image.BRIGHTNESS, self.brightness_var.get())
        self._settings.set(SettingsKeys.Image.CONTRAST, self.contrast_var.get())
        self._settings.set(SettingsKeys.Image.DITHER_MODE, self.dither_var.get())
        self._settings.set(SettingsKeys.Image.ROTATION, int(self.rotation_var.get()))
        self._settings.set(SettingsKeys.Image.INVERT, self.invert_var.get())
        self._settings.save()

    def _init_processor(self) -> None:
        self._processor = ImageProcessor(
            brightness=self.brightness_var.get(),
            contrast=self.contrast_var.get(),
            dither_mode=self.dither_var.get(),
            rotation=int(self.rotation_var.get()),
            invert=self.invert_var.get()
        )

    def _update_processor(self) -> None:
        if self._processor:
            self._processor.brightness = self.brightness_var.get()
            self._processor.contrast = self.contrast_var.get()
            self._processor.dither_mode = self.dither_var.get()
            self._processor.rotation = int(self.rotation_var.get())
            self._processor.invert = self.invert_var.get()

    def _update_value_labels(self) -> None:
        self.brightness_value.configure(text=f"{self.brightness_var.get():.1f}")
        self.contrast_value.configure(text=f"{self.contrast_var.get():.1f}")

    def _on_adjustment_change(self, value=None) -> None:
        self._update_value_labels()
        self._update_processor()
        self._save_settings()

        if self._source_image:
            self._update_preview()

    def _on_option_change(self, value=None) -> None:
        # auto-check show dithering based on dither mode
        if self.dither_var.get() == "none":
            self.show_dither_var.set(False)
        else:
            self.show_dither_var.set(True)

        self._update_processor()
        self._save_settings()

        if self._source_image:
            self._update_preview()

    def save(self) -> None:
        # public method to trigger save called by app for ctrl+s
        self._on_save()

    def _on_show_gallery(self) -> None:
        # ensure templates directory exists
        os.makedirs(self._templates_dir, exist_ok=True)
        TemplateGallery(
            self,
            templates_dir=self._templates_dir,
            on_template_selected=self._on_gallery_image_selected
        )

    def _on_gallery_image_selected(self, filepath: str) -> None:
        # called when user selects an image from the gallery
        self._load_image_file(filepath)

    def _downsample_for_preview(self, image: Image.Image) -> Image.Image:
        # downsample large images to reduce memory usage for preview
        width, height = image.size

        # only downsample if height exceeds threshold
        if height > DOWNSAMPLE_THRESHOLD:
            # calculate new dimensions maintaining aspect ratio
            scale_factor = MAX_PREVIEW_HEIGHT / height
            new_width = int(width * scale_factor)
            new_height = MAX_PREVIEW_HEIGHT

            # use lanczos for high quality downsampling
            downsampled = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            return downsampled

        return image

    def _load_image_file(self, filepath: str) -> None:
        # load an image from the given path
        if filepath:
            try:
                loaded_image = Image.open(filepath)
                self._process_loaded_image(loaded_image, filepath)
            except Exception as e:
                self._handle_image_load_error(e)

    def _process_loaded_image(self, loaded_image: Image.Image, filepath: str) -> None:
        self._original_image_path = filepath
        self._source_image_path = filepath

        status_suffix = self._setup_image_for_preview(loaded_image)

        filename = os.path.basename(filepath)
        self._update_filename_display(filename)

        settings_loaded = self._load_image_settings(filepath)
        self._set_load_status(filename, settings_loaded, status_suffix)
        self._update_preview()

    def _setup_image_for_preview(self, loaded_image: Image.Image) -> str:
        # setup image for preview downsampling if needed
        width, height = loaded_image.size

        if height > DOWNSAMPLE_THRESHOLD:
            self._preview_image = self._downsample_for_preview(loaded_image)
            self._source_image = self._preview_image
            return f" (downsampled from {height}px to {MAX_PREVIEW_HEIGHT}px for preview)"
        else:
            self._preview_image = None
            self._source_image = loaded_image
            return ""

    def _update_filename_display(self, filename: str) -> None:
        self.filename_label.configure(
            text=filename,
            text_color=("gray30", "gray70")
        )

    def _set_load_status(self, filename: str, settings_loaded: bool, suffix: str) -> None:
        if settings_loaded:
            self._set_status(f"Loaded: {filename} (with saved settings){suffix}")
        else:
            self._set_status(f"Loaded: {filename}{suffix}")

    def _handle_image_load_error(self, error: Exception) -> None:
        self._set_status(f"Error loading image: {error}")
        self._source_image = None
        self._source_image_path = None
        self._original_image_path = None
        self._preview_image = None
        self.filename_label.configure(
            text="Error loading image",
            text_color="red"
        )

    def set_source_image(self, image: Image.Image, name: str = "Calendar") -> None:
        # set source image directly from a PIL Image object
        # used by calendar generator and other image-producing features
        # downsample if needed for preview
        width, height = image.size
        if height > DOWNSAMPLE_THRESHOLD:
            self._preview_image = self._downsample_for_preview(image)
            self._source_image = self._preview_image
            status_suffix = f" (downsampled from {height}px to {MAX_PREVIEW_HEIGHT}px for preview)"
        else:
            self._preview_image = None
            self._source_image = image
            status_suffix = ""

        self._source_image_path = None  # no file path for generated images
        self._original_image_path = None

        self.filename_label.configure(
            text=name,
            text_color=("gray30", "gray70")
        )
        self._set_status(f"Generated: {name}{status_suffix}")
        self._update_preview()

    def _update_preview(self) -> None:
        if not self._source_image or not self._processor:
            self.preview_canvas.clear()
            return

        try:
            preview = self._processor.get_full_preview(
                self._source_image,
                show_dithering=self.show_dither_var.get()
            )
            self.preview_canvas.set_image(preview)
        except Exception as e:
            self._set_status(f"Preview error: {e}")

    def _on_print(self) -> None:
        if not self._source_image:
            self._set_status("No image loaded")
            return

        if self._processor:
            try:
                # use full resolution image for printing if available
                if self._original_image_path and os.path.exists(self._original_image_path):
                    # reload full resolution image for printing
                    full_res_image = Image.open(self._original_image_path)
                    processed = self._processor.process(full_res_image)
                    self._set_status("Sending full-resolution image to printer...")
                else:
                    # use preview image for generated or small images
                    processed = self._processor.process(self._source_image)
                    self._set_status("Sending image to printer...")

                # use printer service if available otherwise use legacy callback
                if self._printer_service:
                    self._printer_service.print_image(processed)
                elif self.on_print_request:
                    self.on_print_request(processed)
            except Exception as e:
                self._set_status(f"Error processing image: {e}")

    def _set_status(self, message: str) -> None:
        # use status service if available otherwise use legacy callback
        if self._status_service:
            self._status_service.set_status(message)
        elif self.on_status_change:
            self.on_status_change(message)

    def get_processed_image(self):
        # get processed image using full-resolution if available
        if not self._source_image or not self._processor:
            return None

        # use full resolution image if available
        if self._original_image_path and os.path.exists(self._original_image_path):
            try:
                full_res_image = Image.open(self._original_image_path)
                return self._processor.process(full_res_image)
            except Exception:
                # fall back to preview image if loading fails
                return self._processor.process(self._source_image)

        return self._processor.process(self._source_image)

    def _on_clear(self) -> None:
        self.clear_image()
        self._set_status("Image cleared")

    def _get_settings_path(self, image_path: str) -> str:
        # get the settings file path for an image
        base, _ = os.path.splitext(image_path)
        return f"{base}.pcfg"

    def _get_current_image_settings(self) -> dict:
        # get current image settings as a dictionary
        return {
            "brightness": self.brightness_var.get(),
            "contrast": self.contrast_var.get(),
            "dither_mode": self.dither_var.get(),
            "rotation": int(self.rotation_var.get()),
            "invert": self.invert_var.get(),
        }

    def _apply_image_settings(self, settings: dict) -> None:
        # apply settings from a dictionary to the ui
        if "brightness" in settings:
            self.brightness_var.set(settings["brightness"])
        if "contrast" in settings:
            self.contrast_var.set(settings["contrast"])
        if "dither_mode" in settings:
            self.dither_var.set(settings["dither_mode"])
        if "rotation" in settings:
            self.rotation_var.set(str(settings["rotation"]))
        if "invert" in settings:
            self.invert_var.set(settings["invert"])

        # auto-check show dithering based on dither mode
        if self.dither_var.get() == "none":
            self.show_dither_var.set(False)
        else:
            self.show_dither_var.set(True)

        self._update_value_labels()
        self._update_processor()

    def _load_image_settings(self, image_path: str) -> bool:
        # load settings for an image if a settings file exists
        settings_path = self._get_settings_path(image_path)
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                self._apply_image_settings(settings)
                return True
            except Exception:
                pass
        return False

    def _on_save(self) -> None:
        if not self._source_image:
            self._set_status("No image to save")
            return

        # ensure templates directory exists
        os.makedirs(self._templates_dir, exist_ok=True)

        filepath = save_file_dialog(
            title="Save Image",
            defaultextension=".png",
            filetypes=[("All files", "*.*"), ("PNG files", "*.png"), ("JPEG files", "*.jpg")],
            initialdir=self._templates_dir
        )

        if not filepath:
            return

        try:
            # save image copy
            self._source_image.save(filepath)
            self._source_image_path = filepath

            # save settings alongside
            settings_path = self._get_settings_path(filepath)
            settings = self._get_current_image_settings()
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)

            filename = os.path.basename(filepath)
            self.filename_label.configure(
                text=filename,
                text_color=("gray30", "gray70")
            )
            self._set_status(f"Saved: {filename} (with settings)")
        except Exception as e:
            self._set_status(f"Error saving image: {e}")

    def clear_image(self) -> None:
        self._source_image = None
        self._source_image_path = None
        self._original_image_path = None
        self._preview_image = None
        self.preview_canvas.clear()
        self.filename_label.configure(
            text="No image loaded",
            text_color="gray"
        )
