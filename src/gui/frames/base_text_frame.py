# base class for text input frames with shared ui patterns

from typing import Optional, Callable, List, Tuple, TYPE_CHECKING
from datetime import datetime
import json
import os
import customtkinter as ctk
from tkinter import PanedWindow, VERTICAL

from ...utils.shortcuts import bind_text_shortcuts
from ...config.defaults import (
    DEFAULT_FONT_SIZE,
    MIN_FONT_SIZE,
    MAX_FONT_SIZE,
    TEXT_ALIGN_LEFT,
    TEXT_ALIGN_CENTER,
    TEXT_ALIGN_RIGHT,
    SUPPORTED_TEXT_FORMATS,
    DEFAULT_UNICODE_FONT,
)
from ...config.keys import SettingsKeys
from ...config.settings import get_settings
from ...utils.font_manager import get_font_manager
from ...processing.text_renderer import TextRenderer
from ...processing.image_processor import ImageProcessor
from ..widgets.preview_canvas import PreviewCanvas
from ..widgets.font_selector import FontSelector
from ...utils.file_dialogs import open_file_dialog, save_file_dialog
from ..dialogs.template_gallery import TemplateGallery
from ...utils.unicode_detect import contains_special_unicode, find_unicode_font
from ..dialogs.font_install_dialog import FontInstallDialog, FontSwitchNotification
from ..dialogs.symbols_dialog import SymbolsDialog

# service interfaces
if TYPE_CHECKING:
    from ..interfaces import PrinterService, StatusService, SettingsService
from ..interfaces import create_services_from_app


class BaseTextFrame(ctk.CTkFrame):
    # base class for text and banner frames with shared functionality

    # subclasses should override these
    _settings_section: str = "text"
    _save_dialog_title: str = "Save Template"
    _print_status_message: str = "Sending to printer..."
    _preview_landscape: bool = False
    _renderer_wrap: bool = True
    _templates_dir: str = "gallery/text"

    # maps settings section to SettingsKeys class for subclass namespace isolation
    _section_to_settings_keys = {
        "text": SettingsKeys.Text,
        "banner": SettingsKeys.Banner,
    }

    def _get_settings_keys(self):
        section = self._settings_section
        if section not in self._section_to_settings_keys:
            raise KeyError(
                f"Unknown settings section '{section}'. "
                f"Valid sections: {list(self._section_to_settings_keys.keys())}"
            )
        return self._section_to_settings_keys[section]

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

        # create service adapters from legacy app if services not injected
        if app is not None and (printer_service is None or status_service is None or settings_service is None):
            _printer, _status, _settings, _conn = create_services_from_app(app)
            printer_service = printer_service or _printer
            status_service = status_service or _status
            settings_service = settings_service or _settings

        self._printer_service = printer_service
        self._status_service = status_service
        self._settings_service = settings_service

        # backward compatibility callbacks
        self.on_print_request = on_print_request
        self.on_status_change = on_status_change

        self._settings = settings_service if settings_service else get_settings()
        self._font_manager = get_font_manager()
        self._renderer: Optional[TextRenderer] = None
        self._image_processor: Optional[ImageProcessor] = None
        self._unicode_font_switched = False

        self._setup_ui()
        self._load_settings()
        self._init_renderer()

    def _get_alignment_options(self) -> List[Tuple[str, str]]:
        return [
            ("Left", TEXT_ALIGN_LEFT),
            ("Center", TEXT_ALIGN_CENTER),
            ("Right", TEXT_ALIGN_RIGHT),
        ]

    def _setup_ui(self) -> None:
        label_font = ctk.CTkFont(size=14, weight="bold")
        ctrl_font = ctk.CTkFont(size=14)

        # font controls row
        font_frame = ctk.CTkFrame(self, fg_color="transparent")
        font_frame.pack(fill="x", padx=8, pady=(8, 4))
        self._setup_font_controls(font_frame)

        # alignment darkness and date row
        options_frame = ctk.CTkFrame(self, fg_color="transparent")
        options_frame.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(options_frame, text="Align:", font=label_font, width=50).pack(side="left", padx=(0, 5))

        self.align_var = ctk.StringVar(value=TEXT_ALIGN_LEFT)

        for text, value in self._get_alignment_options():
            ctk.CTkRadioButton(
                options_frame, text=text, variable=self.align_var,
                value=value, command=self._on_alignment_change,
                font=ctrl_font
            ).pack(side="left", padx=(0, 8))

        # darkness controls
        self._setup_darkness_controls(options_frame)

        self.add_date_var = ctk.BooleanVar(value=False)
        self.add_date_check = ctk.CTkCheckBox(
            options_frame, text="Add Date",
            variable=self.add_date_var,
            font=ctrl_font,
            command=self._on_text_change
        )
        self.add_date_check.pack(side="left", padx=(15, 0))

        # pack buttons first to prevent resize hiding them
        button_wrapper = ctk.CTkFrame(self, fg_color="transparent", height=50)
        button_wrapper.pack(side="bottom", fill="x", padx=8, pady=(4, 8))
        button_wrapper.pack_propagate(False)

        button_frame = ctk.CTkFrame(button_wrapper, fg_color="transparent")
        button_frame.pack(fill="x", expand=True, pady=4)

        # resizable paned window for text and preview
        paned_container = ctk.CTkFrame(self)
        paned_container.pack(fill="both", expand=True, padx=8, pady=4)
        paned_container.grid_columnconfigure(0, weight=1)
        paned_container.grid_rowconfigure(0, weight=1)

        # paned window needs tk background matching appearance mode
        paned_bg = "#3B3B3B" if ctk.get_appearance_mode() == "Dark" else "#DBDBDB"
        self.paned = PanedWindow(
            paned_container, orient=VERTICAL,
            sashwidth=8, sashrelief="raised",
            bg=paned_bg
        )
        self.paned.grid(row=0, column=0, sticky="nsew")

        text_container = ctk.CTkFrame(self.paned)
        self.text_input = ctk.CTkTextbox(
            text_container, wrap="word",
            font=ctk.CTkFont(family="monospace", size=13),
            undo=True
        )
        self.text_input.pack(fill="both", expand=True, padx=2, pady=2)
        self.text_input.bind("<KeyRelease>", self._on_text_change)
        self._bind_shortcuts()

        self.paned.add(text_container, minsize=100, height=200)

        preview_container = ctk.CTkFrame(self.paned)
        self.preview_canvas = PreviewCanvas(
            preview_container,
            height=100,
            landscape=self._preview_landscape
        )
        self.preview_canvas.pack(fill="both", expand=True, padx=2, pady=2)

        self.paned.add(preview_container, minsize=80, height=120)

        btn_width = 100
        btn_height = 36
        btn_font = ctk.CTkFont(size=14)
        filename_font = ctk.CTkFont(size=15)

        ctk.CTkButton(
            button_frame, text="Gallery", width=btn_width, height=btn_height,
            font=btn_font,
            command=self._on_show_gallery
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            button_frame, text="Clear", width=btn_width, height=btn_height,
            font=btn_font,
            command=self._on_clear
        ).pack(side="left", padx=(0, 8))

        self.filename_label = ctk.CTkLabel(
            button_frame,
            text="No file loaded",
            text_color="gray",
            font=filename_font
        )
        self.filename_label.pack(side="left", fill="x", expand=True, padx=(8, 8))

        self.print_button = ctk.CTkButton(
            button_frame, text="Print", width=btn_width, height=btn_height,
            font=btn_font,
            fg_color=("green", "#00AA00"),
            hover_color=("darkgreen", "#008800"),
            command=self._on_print
        )
        self.print_button.pack(side="right")

        ctk.CTkButton(
            button_frame, text="Save", width=btn_width, height=btn_height,
            font=btn_font,
            command=self._on_save_template
        ).pack(side="right", padx=(0, 8))

    # -------------------------------------------------------------------------
    # font controls
    # -------------------------------------------------------------------------
    def _setup_font_controls(self, parent_frame: ctk.CTkFrame) -> None:
        label_font = ctk.CTkFont(size=14, weight="bold")
        ctrl_font = ctk.CTkFont(size=14)

        ctk.CTkLabel(parent_frame, text="Font:", font=label_font, width=50).pack(side="left", padx=(0, 5))

        families = self._font_manager.get_available_families()
        if not families:
            families = ["Default"]
        self._font_families = families

        self.font_selector = FontSelector(
            parent_frame,
            fonts=self._font_families,
            command=self._on_font_change,
            width=240,
            height=36
        )
        self.font_selector.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(parent_frame, text="Size:", font=label_font).pack(side="left", padx=(0, 5))

        self.font_size_var = ctk.IntVar(value=DEFAULT_FONT_SIZE)
        self.size_entry = ctk.CTkEntry(
            parent_frame,
            textvariable=self.font_size_var,
            width=60,
            height=32,
            font=ctrl_font
        )
        self.size_entry.pack(side="left", padx=(0, 4))
        self.size_entry.bind("<Return>", lambda e: self._on_font_change())
        self.size_entry.bind("<FocusOut>", lambda e: self._on_font_change())

        ctk.CTkButton(
            parent_frame, text="-", width=36, height=32, font=ctrl_font,
            command=lambda: self._change_size(-2)
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            parent_frame, text="+", width=36, height=32, font=ctrl_font,
            command=lambda: self._change_size(2)
        ).pack(side="left", padx=(2, 20))

        self.bold_var = ctk.BooleanVar(value=False)
        self.bold_button = ctk.CTkCheckBox(
            parent_frame, text="Bold", variable=self.bold_var,
            font=ctrl_font, command=self._on_font_change
        )
        self.bold_button.pack(side="left", padx=(0, 5))

        self.italic_var = ctk.BooleanVar(value=False)
        self.italic_button = ctk.CTkCheckBox(
            parent_frame, text="Italic", variable=self.italic_var,
            font=ctrl_font, command=self._on_font_change
        )
        self.italic_button.pack(side="left", padx=(0, 10))

        self.symbols_button = ctk.CTkButton(
            parent_frame, text="Symbols", width=70, height=32,
            font=ctrl_font, command=self._on_math_symbols
        )
        self.symbols_button.pack(side="left")

    def _on_font_change(self, *args) -> None:
        try:
            size = int(self.font_size_var.get())
            size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, size))
            self.font_size_var.set(size)
        except ValueError:
            self.font_size_var.set(DEFAULT_FONT_SIZE)

        self._update_style_buttons()

        if self._renderer:
            self._renderer.update_font(
                font_family=self.font_selector.get(),
                font_size=self.font_size_var.get(),
                bold=self.bold_var.get(),
                italic=self.italic_var.get()
            )

        self._save_settings()
        self._update_preview()

    def _change_size(self, delta: int) -> None:
        try:
            current = int(self.font_size_var.get())
            new_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, current + delta))
            self.font_size_var.set(new_size)
            self._on_font_change()
        except ValueError:
            pass

    def _update_style_buttons(self) -> None:
        family = self.font_selector.get()
        styles = self._font_manager.get_family_styles(family)

        has_bold = any(s in styles for s in ["Bold", "SemiBold", "Medium"])
        self.bold_button.configure(state="normal" if has_bold else "disabled")
        if not has_bold:
            self.bold_var.set(False)

        has_italic = any(s in styles for s in ["Italic", "Oblique"])
        self.italic_button.configure(state="normal" if has_italic else "disabled")
        if not has_italic:
            self.italic_var.set(False)

    # -------------------------------------------------------------------------
    # darkness controls
    # -------------------------------------------------------------------------
    def _setup_darkness_controls(self, parent_frame: ctk.CTkFrame) -> None:
        label_font = ctk.CTkFont(size=14, weight="bold")
        ctrl_font = ctk.CTkFont(size=14)

        ctk.CTkLabel(parent_frame, text="Darkness:", font=label_font).pack(side="left", padx=(20, 5))

        self.darkness_var = ctk.DoubleVar(value=1.5)
        self.darkness_slider = ctk.CTkSlider(
            parent_frame, from_=0.3, to=3.0, variable=self.darkness_var,
            width=180, height=20, command=self._on_darkness_slider_change
        )
        self.darkness_slider.pack(side="left", padx=(0, 5))

        self.darkness_entry = ctk.CTkEntry(parent_frame, width=50, font=ctrl_font, justify="center")
        self.darkness_entry.pack(side="left")
        self.darkness_entry.insert(0, "1.5")
        self.darkness_entry.bind("<Return>", self._on_darkness_entry_change)
        self.darkness_entry.bind("<FocusOut>", self._on_darkness_entry_change)

    def _update_darkness_entry(self) -> None:
        self.darkness_entry.delete(0, "end")
        self.darkness_entry.insert(0, f"{self.darkness_var.get():.2f}")

    def _on_darkness_slider_change(self, value=None) -> None:
        self._update_darkness_entry()
        if self._image_processor:
            self._image_processor.contrast = self.darkness_var.get()
        self._save_settings()
        self._update_preview()

    def _on_darkness_entry_change(self, event=None) -> None:
        try:
            value = float(self.darkness_entry.get())
            value = max(0.3, min(3.0, value))
            self.darkness_var.set(value)
            self._update_darkness_entry()
            if self._image_processor:
                self._image_processor.contrast = value
            self._save_settings()
            self._update_preview()
        except ValueError:
            self._update_darkness_entry()

    # -------------------------------------------------------------------------
    # template file operations
    # -------------------------------------------------------------------------
    def _on_show_gallery(self) -> None:
        os.makedirs(self._templates_dir, exist_ok=True)
        TemplateGallery(
            self,
            templates_dir=self._templates_dir,
            on_template_selected=self._on_gallery_template_selected
        )

    def _on_gallery_template_selected(self, filepath: str) -> None:
        self._load_text_file(filepath)

    def _load_text_file(self, filepath: str) -> None:
        if not filepath:
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            self.text_input.delete("1.0", "end")
            self.text_input.insert("1.0", content)

            settings_loaded = self._load_file_settings(filepath)

            filename = os.path.basename(filepath)
            self.filename_label.configure(text=filename, text_color=("gray30", "gray70"))

            if settings_loaded:
                self._set_status(f"Loaded: {filename} (with saved settings)")
            else:
                self._set_status(f"Loaded: {filename}")

            self._update_preview()
        except Exception as e:
            self._set_status(f"Error loading file: {e}")
            self.filename_label.configure(text="Error loading file", text_color="red")

    def _get_settings_path(self, text_path: str) -> str:
        base, _ = os.path.splitext(text_path)
        return f"{base}.pcfg"

    def _load_file_settings(self, text_path: str) -> bool:
        settings_path = self._get_settings_path(text_path)
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                self._apply_loaded_settings(settings)
                return True
            except Exception:
                pass
        return False

    def _apply_loaded_settings(self, settings: dict) -> None:
        if "font_family" in settings and settings["font_family"] in self._font_families:
            self.font_selector.set(settings["font_family"])
        if "font_size" in settings:
            self.font_size_var.set(settings["font_size"])
        if "bold" in settings:
            self.bold_var.set(settings["bold"])
        if "italic" in settings:
            self.italic_var.set(settings["italic"])
        if "alignment" in settings:
            self.align_var.set(settings["alignment"])
        if "darkness" in settings:
            self.darkness_var.set(settings["darkness"])
        if "add_date" in settings:
            self.add_date_var.set(settings["add_date"])

        self._update_darkness_entry()
        self._update_style_buttons()

        if self._renderer:
            self._renderer.update_font(
                font_family=self.font_selector.get(),
                font_size=self.font_size_var.get(),
                bold=self.bold_var.get(),
                italic=self.italic_var.get()
            )
            self._renderer.set_alignment(self.align_var.get())

        if self._image_processor:
            self._image_processor.contrast = self.darkness_var.get()

    def _on_save_template(self) -> None:
        text = self.text_input.get("1.0", "end").strip()
        if not text:
            self._set_status("No text to save")
            return

        os.makedirs(self._templates_dir, exist_ok=True)

        filepath = save_file_dialog(
            title=self._save_dialog_title,
            defaultextension=".txt",
            filetypes=[("All files", "*.*"), ("Text files", "*.txt")],
            initialdir=self._templates_dir
        )

        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(text)

                settings_path = self._get_settings_path(filepath)
                settings = self._get_current_settings()
                with open(settings_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2)

                filename = os.path.basename(filepath)
                self._set_status(f"Saved: {filename} (with settings)")
            except Exception as e:
                self._set_status(f"Error saving file: {e}")

    # -------------------------------------------------------------------------
    # remaining methods
    # -------------------------------------------------------------------------
    def _bind_shortcuts(self) -> None:
        bind_text_shortcuts(
            self,
            self.text_input._textbox,
            on_change=self._on_text_change
        )

    def save(self) -> None:
        # public method called by app for ctrl+s
        self._on_save_template()

    def _load_settings(self) -> None:
        section = self._settings.get_section(self._settings_section)

        font_family = section.get("font_family", "")
        if font_family and font_family in self._font_families:
            self.font_selector.set(font_family)

        self.font_size_var.set(section.get("font_size", DEFAULT_FONT_SIZE))
        self.bold_var.set(section.get("bold", False))
        self.italic_var.set(section.get("italic", False))
        self.align_var.set(section.get("alignment", TEXT_ALIGN_LEFT))
        self.darkness_var.set(section.get("darkness", 1.5))
        self.add_date_var.set(section.get("add_date", False))
        self._update_darkness_entry()
        self._update_style_buttons()

    def _save_settings(self) -> None:
        keys = self._get_settings_keys()
        self._settings.set(keys.FONT_FAMILY, self.font_selector.get())
        self._settings.set(keys.FONT_SIZE, self.font_size_var.get())
        self._settings.set(keys.BOLD, self.bold_var.get())
        self._settings.set(keys.ITALIC, self.italic_var.get())
        self._settings.set(keys.ALIGNMENT, self.align_var.get())
        self._settings.set(keys.DARKNESS, self.darkness_var.get())
        self._settings.set(keys.ADD_DATE, self.add_date_var.get())
        self._settings.save()

    def _init_renderer(self) -> None:
        self._renderer = TextRenderer(
            font_family=self.font_selector.get(),
            font_size=self.font_size_var.get(),
            bold=self.bold_var.get(),
            italic=self.italic_var.get(),
            alignment=self.align_var.get(),
            wrap=self._renderer_wrap
        )
        darkness = self.darkness_var.get()
        self._image_processor = ImageProcessor(
            brightness=1.0,
            contrast=darkness,
            auto_resize=False
        )

    def _on_alignment_change(self) -> None:
        if self._renderer:
            self._renderer.set_alignment(self.align_var.get())
        self._save_settings()
        self._update_preview()

    def _on_text_change(self, event=None) -> None:
        if hasattr(self, '_preview_after_id'):
            self.after_cancel(self._preview_after_id)
        self._preview_after_id = self.after(500, self._update_preview)

        if hasattr(self, '_unicode_check_id'):
            self.after_cancel(self._unicode_check_id)
        self._unicode_check_id = self.after(300, self._check_unicode_font)

    def _check_unicode_font(self) -> None:
        # auto-switch to unicode font if special characters detected
        text = self.text_input.get("1.0", "end").strip()
        current_font = self.font_selector.get()

        # get preferred unicode font from settings
        preferred_font = self._settings.get(
            SettingsKeys.Unicode.PREFERRED_FONT, DEFAULT_UNICODE_FONT
        )
        unicode_font = find_unicode_font(self._font_families, preferred_font)

        if unicode_font and current_font == unicode_font:
            return

        if contains_special_unicode(text):
            if unicode_font:
                original_font = current_font
                self.font_selector.set(unicode_font)
                self._on_font_change()

                if self._settings.get(SettingsKeys.Unicode.SHOW_FONT_SWITCH_POPUP, True):
                    self.after(100, lambda: self._show_font_switch_popup(original_font, unicode_font))
            else:
                if not self._unicode_font_switched:
                    self._unicode_font_switched = True
                    self.after(100, self._show_font_install_dialog)

    def _show_font_switch_popup(self, original_font: str, new_font: str) -> None:
        def on_disable():
            self._settings.set(SettingsKeys.Unicode.SHOW_FONT_SWITCH_POPUP, False)
            self._settings.save()

        FontSwitchNotification(
            self.winfo_toplevel(),
            original_font=original_font,
            new_font=new_font,
            on_disable_popup=on_disable
        )

    def _show_font_install_dialog(self) -> None:
        FontInstallDialog(self.winfo_toplevel())

    def _on_math_symbols(self) -> None:
        SymbolsDialog(
            self.winfo_toplevel(),
            on_insert=self._insert_math_symbols
        )

    def _insert_math_symbols(self, symbols: str) -> None:
        if not symbols:
            return

        current_text = self.text_input.get("1.0", "end-1c")
        # add space if text doesnt end with whitespace
        if current_text and not current_text.endswith(" ") and not current_text.endswith("\n"):
            symbols = " " + symbols

        self.text_input.insert("end", symbols)
        self._on_text_change()
        self._set_status("Math symbols inserted")

    def _get_date_string(self) -> str:
        keys = self._get_settings_keys()
        date_format = self._settings.get(keys.DATE_FORMAT, "%Y-%m-%d %H:%M")
        return datetime.now().strftime(date_format)

    def _get_print_text(self) -> str:
        text = self.text_input.get("1.0", "end").strip()
        if self.add_date_var.get() and text:
            date_str = self._get_date_string()
            text = f"{date_str}\n\n{text}"
        return text

    def _get_current_settings(self) -> dict:
        return {
            "font_family": self.font_selector.get(),
            "font_size": self.font_size_var.get(),
            "bold": self.bold_var.get(),
            "italic": self.italic_var.get(),
            "alignment": self.align_var.get(),
            "darkness": self.darkness_var.get(),
            "add_date": self.add_date_var.get(),
        }

    def _on_clear(self) -> None:
        self.text_input.delete("1.0", "end")
        self.preview_canvas.clear()
        self.filename_label.configure(text="No file loaded", text_color="gray")
        self._set_status("Text cleared")

    def _process_image_for_preview(self, rgb_image):
        return rgb_image

    def _process_image_for_print(self, rgb_image):
        return rgb_image

    def _update_preview(self) -> None:
        text = self._get_print_text()
        if not text:
            self.preview_canvas.clear()
            return

        if self._renderer and self._image_processor:
            try:
                rgb_image = self._renderer.render(text)
                rgb_image = self._process_image_for_preview(rgb_image)
                preview = self._image_processor.get_full_preview(
                    rgb_image,
                    show_dithering=False
                )
                self.preview_canvas.set_image(preview)
            except Exception as e:
                self._set_status(f"Preview error: {e}")

    def _on_print(self) -> None:
        text = self._get_print_text()
        if not text:
            self._set_status("No text to print")
            return

        if self._renderer and self._image_processor:
            try:
                rgb_image = self._renderer.render(text)
                rgb_image = self._process_image_for_print(rgb_image)
                processed_image = self._image_processor.process(rgb_image)

                if self._printer_service:
                    self._printer_service.print_image(processed_image)
                elif self.on_print_request:
                    self.on_print_request(processed_image)

                self._set_status(self._print_status_message)
            except Exception as e:
                self._set_status(f"Error rendering: {e}")

    def _set_status(self, message: str) -> None:
        if self._status_service:
            self._status_service.set_status(message)
        elif self.on_status_change:
            self.on_status_change(message)

    def get_rendered_image(self):
        text = self._get_print_text()
        if text and self._renderer and self._image_processor:
            rgb_image = self._renderer.render(text)
            rgb_image = self._process_image_for_print(rgb_image)
            return self._image_processor.process(rgb_image)
        return None
