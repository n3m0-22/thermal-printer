# template frame for creating templates with draggable text areas

from typing import Optional, Callable, List, TYPE_CHECKING
import json
import os
import customtkinter as ctk
from tkinter import PanedWindow, VERTICAL
from PIL import Image

from ...config.defaults import (
    DEFAULT_FONT_SIZE,
    DEFAULT_FONT_FAMILY,
    DEFAULT_TEXT_ALIGN,
    MIN_FONT_SIZE,
    MAX_FONT_SIZE,
    TEXT_ALIGN_LEFT,
    TEXT_ALIGN_CENTER,
    TEXT_ALIGN_RIGHT,
    SUPPORTED_IMAGE_FORMATS,
)
from ...config.keys import SettingsKeys
from ...config.settings import get_settings
from ...processing.label_renderer import (
    LabelRenderer,
    TextAreaConfig,
)
from ...processing.image_processor import ImageProcessor
from ..widgets.interactive_canvas import InteractiveCanvas
from ..widgets.font_selector import FontSelector
from ..dialogs.template_gallery import TemplateGallery
from ..dialogs.calendar_dialog import CalendarDialog
from ...utils.file_dialogs import open_file_dialog, save_file_dialog
from ...utils.font_manager import get_font_manager
from ...utils.shortcuts import bind_text_shortcuts
from ..managers.text_area_manager import TextAreaManager, TextAreaUIState
from ..managers.template_io_manager import TemplateIOManager
from ..managers.template_settings_manager import TemplateSettingsManager

# service interfaces
if TYPE_CHECKING:
    from ..interfaces import PrinterService, StatusService, SettingsService
from ..interfaces import create_services_from_app


class TemplateFrame(ctk.CTkFrame):

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
        self._renderer = LabelRenderer()

        # initialize template settings manager
        self._settings_manager = TemplateSettingsManager(settings_service)

        # initialize template io manager
        self._io_manager = TemplateIOManager(
            on_status=self._set_status,
            on_template_loaded=self._on_template_loaded_callback,
            save_dir="gallery/templates"
        )

        # text areas management via manager
        self._text_area_manager = TextAreaManager(
            on_areas_changed=self._on_manager_areas_changed,
            on_area_selected=self._on_manager_area_selected,
            on_status=self._set_status
        )

        self._setup_ui()
        self._load_settings()
        # dont add default text area as user adds them as needed
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
        label_font = ctk.CTkFont(size=14, weight="bold")
        ctrl_font = ctk.CTkFont(size=14)
        btn_font = ctk.CTkFont(size=14)

        # bottom buttons first so always visible
        button_wrapper = ctk.CTkFrame(self, fg_color="transparent", height=50)
        button_wrapper.pack(side="bottom", fill="x", padx=10, pady=(5, 10))
        button_wrapper.pack_propagate(False)

        button_frame = ctk.CTkFrame(button_wrapper, fg_color="transparent")
        button_frame.pack(fill="x", expand=True, pady=4)

        btn_width = 100
        btn_height = 36

        self.gallery_button = ctk.CTkButton(
            button_frame,
            text="Gallery",
            width=btn_width,
            height=btn_height,
            font=btn_font,
            command=self._on_show_gallery
        )
        self.gallery_button.pack(side="left", padx=(0, 8))

        self.clear_template_btn = ctk.CTkButton(
            button_frame,
            text="Clear",
            width=btn_width,
            height=btn_height,
            font=btn_font,
            command=self._on_clear_template
        )
        self.clear_template_btn.pack(side="left", padx=(0, 8))

        self.template_label = ctk.CTkLabel(
            button_frame,
            text="No template loaded",
            text_color="gray",
            font=ctk.CTkFont(size=15)
        )
        self.template_label.pack(side="left", fill="x", expand=True, padx=(8, 8))

        self.print_button = ctk.CTkButton(
            button_frame,
            text="Print",
            width=btn_width,
            height=btn_height,
            font=btn_font,
            fg_color=("green", "#00AA00"),
            hover_color=("darkgreen", "#008800"),
            command=self._on_print
        )
        self.print_button.pack(side="right")

        self.save_button = ctk.CTkButton(
            button_frame,
            text="Save",
            width=btn_width,
            height=btn_height,
            font=btn_font,
            command=self._on_save_label
        )
        self.save_button.pack(side="right", padx=8)

        # text areas management row
        areas_frame = ctk.CTkFrame(self, fg_color="transparent")
        areas_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            areas_frame,
            text="Areas:",
            font=label_font,
            width=75,
            anchor="w"
        ).pack(side="left", padx=(0, 5))

        self.add_area_btn = ctk.CTkButton(
            areas_frame,
            text="+ Add",
            width=70,
            height=32,
            font=btn_font,
            command=self._on_add_text_area
        )
        self.add_area_btn.pack(side="left", padx=(0, 5))

        self.area_selector = ctk.CTkOptionMenu(
            areas_frame,
            values=["Area 1"],
            width=150,
            height=32,
            font=ctrl_font,
            dynamic_resizing=False,
            command=self._on_area_selected
        )
        self.area_selector.pack(side="left", padx=(0, 5))

        self.remove_area_btn = ctk.CTkButton(
            areas_frame,
            text="Remove",
            width=70,
            height=32,
            font=btn_font,
            command=self._on_remove_text_area
        )
        self.remove_area_btn.pack(side="left", padx=(0, 5))

        self.delete_all_btn = ctk.CTkButton(
            areas_frame,
            text="Delete All",
            width=80,
            height=32,
            font=btn_font,
            command=self._on_delete_all_areas
        )
        self.delete_all_btn.pack(side="left", padx=(0, 5))

        self.reset_btn = ctk.CTkButton(
            areas_frame,
            text="Reset",
            width=60,
            height=32,
            font=btn_font,
            command=self._on_reset_areas
        )
        self.reset_btn.pack(side="left", padx=(0, 15))

        # position controls
        ctk.CTkLabel(
            areas_frame,
            text="X:",
            font=label_font
        ).pack(side="left", padx=(0, 2))

        self.x_var = ctk.IntVar(value=10)
        self.x_entry = ctk.CTkEntry(
            areas_frame,
            textvariable=self.x_var,
            width=60,
            height=32,
            font=ctrl_font
        )
        self.x_entry.pack(side="left", padx=(0, 10))
        self.x_entry.bind("<Return>", lambda e: self._on_position_change())
        self.x_entry.bind("<FocusOut>", lambda e: self._on_position_change())

        ctk.CTkLabel(
            areas_frame,
            text="Y:",
            font=label_font
        ).pack(side="left", padx=(0, 2))

        self.y_var = ctk.IntVar(value=10)
        self.y_entry = ctk.CTkEntry(
            areas_frame,
            textvariable=self.y_var,
            width=60,
            height=32,
            font=ctrl_font
        )
        self.y_entry.pack(side="left", padx=(0, 15))
        self.y_entry.bind("<Return>", lambda e: self._on_position_change())
        self.y_entry.bind("<FocusOut>", lambda e: self._on_position_change())

        self.calendar_button = ctk.CTkButton(
            areas_frame,
            text="Calendar",
            width=80,
            height=32,
            font=btn_font,
            command=self._on_calendar
        )
        self.calendar_button.pack(side="left")

        # font controls row
        font_frame = ctk.CTkFrame(self, fg_color="transparent")
        font_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            font_frame,
            text="Font:",
            font=label_font,
            width=75,
            anchor="w"
        ).pack(side="left", padx=(0, 5))

        font_manager = get_font_manager()
        available_fonts = font_manager.get_available_families()

        self.font_selector = FontSelector(
            font_frame,
            fonts=available_fonts,
            command=self._on_font_change,
            width=180,
            height=32
        )
        self.font_selector.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            font_frame,
            text="Size:",
            font=label_font
        ).pack(side="left", padx=(0, 5))

        self.font_size_var = ctk.IntVar(value=DEFAULT_FONT_SIZE)
        self.font_size_entry = ctk.CTkEntry(
            font_frame,
            textvariable=self.font_size_var,
            width=50,
            height=32,
            font=ctrl_font
        )
        self.font_size_entry.pack(side="left", padx=(0, 2))

        self.size_minus_btn = ctk.CTkButton(
            font_frame,
            text="-",
            width=32,
            height=32,
            font=btn_font,
            command=lambda: self._adjust_font_size(-2)
        )
        self.size_minus_btn.pack(side="left", padx=(0, 2))

        self.size_plus_btn = ctk.CTkButton(
            font_frame,
            text="+",
            width=32,
            height=32,
            font=btn_font,
            command=lambda: self._adjust_font_size(2)
        )
        self.size_plus_btn.pack(side="left", padx=(0, 15))

        self.bold_var = ctk.BooleanVar(value=False)
        self.bold_check = ctk.CTkCheckBox(
            font_frame,
            text="Bold",
            variable=self.bold_var,
            font=ctrl_font,
            command=self._on_style_change
        )
        self.bold_check.pack(side="left", padx=(0, 10))

        self.italic_var = ctk.BooleanVar(value=False)
        self.italic_check = ctk.CTkCheckBox(
            font_frame,
            text="Italic",
            variable=self.italic_var,
            font=ctrl_font,
            command=self._on_style_change
        )
        self.italic_check.pack(side="left", padx=(0, 25))

        # alignment controls on same row as bold/italic
        align_frame = ctk.CTkFrame(self, fg_color="transparent")
        align_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            align_frame,
            text="Align:",
            font=label_font,
            width=75,
            anchor="w"
        ).pack(side="left", padx=(0, 5))

        self.align_var = ctk.StringVar(value=TEXT_ALIGN_LEFT)
        self.align_left = ctk.CTkRadioButton(
            align_frame,
            text="Left",
            variable=self.align_var,
            value=TEXT_ALIGN_LEFT,
            font=ctrl_font,
            command=self._on_style_change
        )
        self.align_left.pack(side="left", padx=(0, 10))

        self.align_center = ctk.CTkRadioButton(
            align_frame,
            text="Center",
            variable=self.align_var,
            value=TEXT_ALIGN_CENTER,
            font=ctrl_font,
            command=self._on_style_change
        )
        self.align_center.pack(side="left", padx=(0, 10))

        self.align_right = ctk.CTkRadioButton(
            align_frame,
            text="Right",
            variable=self.align_var,
            value=TEXT_ALIGN_RIGHT,
            font=ctrl_font,
            command=self._on_style_change
        )
        self.align_right.pack(side="left", padx=(0, 25))

        ctk.CTkLabel(
            align_frame,
            text="Darkness:",
            font=label_font
        ).pack(side="left", padx=(0, 5))

        self.darkness_var = ctk.DoubleVar(value=1.5)
        self.darkness_slider = ctk.CTkSlider(
            align_frame,
            from_=0.5,
            to=3.0,
            variable=self.darkness_var,
            width=150,
            height=20,
            command=self._on_darkness_slider_change
        )
        self.darkness_slider.pack(side="left", padx=(0, 5))

        self.darkness_entry = ctk.CTkEntry(
            align_frame,
            width=50,
            font=ctrl_font,
            justify="center"
        )
        self.darkness_entry.pack(side="left")
        self.darkness_entry.insert(0, "1.50")
        self.darkness_entry.bind("<Return>", self._on_darkness_entry_change)
        self.darkness_entry.bind("<FocusOut>", self._on_darkness_entry_change)

        # resizable paned window for text and preview (like Text/Banner tabs)
        paned_container = ctk.CTkFrame(self)
        paned_container.pack(fill="both", expand=True, padx=10, pady=5)
        paned_container.grid_columnconfigure(0, weight=1)
        paned_container.grid_rowconfigure(0, weight=1)

        # use mode-appropriate background color for paned window
        paned_bg = "#3B3B3B" if ctk.get_appearance_mode() == "Dark" else "#DBDBDB"
        self.paned = PanedWindow(
            paned_container, orient=VERTICAL,
            sashwidth=8, sashrelief="raised",
            bg=paned_bg
        )
        self.paned.grid(row=0, column=0, sticky="nsew")

        # text input container
        text_container = ctk.CTkFrame(self.paned)
        self.text_input = ctk.CTkTextbox(
            text_container,
            wrap="word",
            font=ctk.CTkFont(family="monospace", size=13),
            undo=True
        )
        self.text_input.pack(fill="both", expand=True, padx=2, pady=2)
        self.text_input.bind("<KeyRelease>", self._on_text_change)

        # bind keyboard shortcuts ctrl+c ctrl+v ctrl+x ctrl+a ctrl+z ctrl+y
        bind_text_shortcuts(self, self.text_input._textbox, self._on_text_change)

        self.paned.add(text_container, minsize=60, height=100)

        # interactive preview canvas with drag-and-drop
        preview_container = ctk.CTkFrame(self.paned)
        self.preview_canvas = InteractiveCanvas(
            preview_container,
            on_area_selected=self._on_canvas_area_selected,
            on_area_moved=self._on_canvas_area_moved,
            on_area_added=self._on_canvas_area_added
        )
        self.preview_canvas.pack(fill="both", expand=True, padx=2, pady=2)

        self.paned.add(preview_container, minsize=100, height=200)

    def _setup_shortcuts(self) -> None:
        # bind keyboard shortcuts to the interactive canvas
        # shortcuts only work when canvas has focus
        canvas = self.preview_canvas.canvas

        # delete key to delete selected area
        canvas.bind("<Delete>", self._on_delete_key)
        canvas.bind("<BackSpace>", self._on_delete_key)

        # arrow keys to nudge position
        canvas.bind("<Up>", lambda e: self._nudge_position(0, -1))
        canvas.bind("<Down>", lambda e: self._nudge_position(0, 1))
        canvas.bind("<Left>", lambda e: self._nudge_position(-1, 0))
        canvas.bind("<Right>", lambda e: self._nudge_position(1, 0))

        # shift+arrow for larger nudge
        canvas.bind("<Shift-Up>", lambda e: self._nudge_position(0, -10))
        canvas.bind("<Shift-Down>", lambda e: self._nudge_position(0, 10))
        canvas.bind("<Shift-Left>", lambda e: self._nudge_position(-10, 0))
        canvas.bind("<Shift-Right>", lambda e: self._nudge_position(10, 0))

        # make canvas focusable
        canvas.configure(takefocus=True)
        canvas.bind("<Button-1>", lambda e: canvas.focus_set(), add="+")

    def _on_delete_key(self, event=None) -> None:
        # remove the selected text area
        if self._text_area_manager.current_index >= 0 and len(self._text_area_manager.text_areas) > 0:
            self._on_remove_text_area()
        return "break"

    def _nudge_position(self, dx: int, dy: int) -> None:
        # nudge selected text area position
        template_image = self._io_manager.template_image
        if self._text_area_manager.current_index < 0 or not template_image:
            return "break"

        area = self._text_area_manager.current_area

        # calculate new position
        new_x = max(0, min(area.x + dx, template_image.width - 10))
        new_y = max(0, min(area.y + dy, template_image.height - 10))

        area.x = new_x
        area.y = new_y

        self.x_var.set(new_x)
        self.y_var.set(new_y)

        self._update_preview()
        return "break"

    def _load_settings(self) -> None:
        darkness = self._settings_manager.load()
        self.darkness_var.set(darkness)
        self._update_darkness_entry()

    def _save_settings(self) -> None:
        self._settings_manager.darkness = self.darkness_var.get()

    def _on_manager_areas_changed(self, names: List[str]) -> None:
        # callback when text areas list changes
        self.area_selector.configure(values=names)
        if names and names[0] != "(none)":
            current_index = self._text_area_manager.current_index
            if 0 <= current_index < len(names):
                self.area_selector.set(names[current_index])
        else:
            self.area_selector.set("(none)")

    def _on_manager_area_selected(self, index: int) -> None:
        # callback when text area selection changes
        if index >= 0:
            self._load_current_area_to_ui()
        else:
            self._clear_ui_fields()
        self._update_preview()

    def _load_current_area_to_ui(self) -> None:
        # load current text area settings into ui controls
        state = self._text_area_manager.get_current_ui_state()
        if state is None:
            return

        self.x_var.set(state.x)
        self.y_var.set(state.y)
        self.font_selector.set(state.font_family)
        self.font_size_var.set(state.font_size)
        self.bold_var.set(state.bold)
        self.italic_var.set(state.italic)
        self.align_var.set(state.alignment)

        # update text entry (CTkTextbox API)
        self.text_input.delete("1.0", "end")
        self.text_input.insert("1.0", state.text)

    def _save_current_area_from_ui(self) -> None:
        # save ui values to current text area
        try:
            x = self.x_var.get()
        except Exception:
            x = 10

        try:
            y = self.y_var.get()
        except Exception:
            y = 10

        state = TextAreaUIState(
            x=x,
            y=y,
            font_family=self.font_selector.get(),
            font_size=self.font_size_var.get(),
            bold=self.bold_var.get(),
            italic=self.italic_var.get(),
            alignment=self.align_var.get(),
            text=self.text_input.get("1.0", "end-1c")
        )
        self._text_area_manager.update_current_from_ui(state)

    def _on_area_selected(self, value: str) -> None:
        # save current area before switching
        self._save_current_area_from_ui()

        # select the area via manager
        if self._text_area_manager.select_by_name(value):
            self.preview_canvas.set_selected_index(self._text_area_manager.current_index)

    def _on_canvas_area_selected(self, index: int) -> None:
        # called when user clicks on text area in canvas
        if index < 0:
            return

        # save current area before switching
        self._save_current_area_from_ui()

        # select via manager (will trigger callback)
        self._text_area_manager.select_by_index(index)

    def _on_canvas_area_moved(self, index: int, new_x: int, new_y: int) -> None:
        # called when user drags text area to new position
        self._text_area_manager.on_area_moved(index, new_x, new_y)

        # update ui if this is the current area
        if index == self._text_area_manager.current_index:
            self.x_var.set(new_x)
            self.y_var.set(new_y)

        self._update_preview()

    def _on_canvas_area_added(self, new_area: TextAreaConfig) -> None:
        # called when user pastes a copied area from canvas
        # save current area first
        self._save_current_area_from_ui()

        # add via manager (will trigger callbacks)
        self._text_area_manager.on_area_added(new_area)

        self._update_preview()

    def _on_add_text_area(self) -> None:
        # save current area first
        self._save_current_area_from_ui()

        # add via manager (will trigger callbacks)
        self._text_area_manager.add_area()

        self._update_preview()

    def _on_remove_text_area(self) -> None:
        if self._text_area_manager.remove_current():
            self._update_preview()

    def _on_delete_all_areas(self) -> None:
        if self._text_area_manager.delete_all() > 0:
            self._update_preview()

    def _on_reset_areas(self) -> None:
        # clear text content from all areas but keep positions
        self._text_area_manager.reset_all_text()
        self._load_current_area_to_ui()
        self._update_preview()

    def _clear_ui_fields(self) -> None:
        # clear the UI input fields when no areas exist
        self.x_var.set(10)
        self.y_var.set(10)
        self.text_input.delete("1.0", "end")

    def _on_position_change(self) -> None:
        self._save_current_area_from_ui()
        self._update_preview()

    def _on_font_change(self, font_name: str) -> None:
        self._save_current_area_from_ui()
        self._update_preview()

    def _adjust_font_size(self, delta: int) -> None:
        new_size = self.font_size_var.get() + delta
        new_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, new_size))
        self.font_size_var.set(new_size)
        self._save_current_area_from_ui()
        self._update_preview()

    def _on_style_change(self) -> None:
        self._save_current_area_from_ui()
        self._update_preview()

    def _on_text_change(self, event=None) -> None:
        self._save_current_area_from_ui()
        # debounce preview updates
        if hasattr(self, '_text_update_after'):
            self.after_cancel(self._text_update_after)
        self._text_update_after = self.after(200, self._update_preview)

    def _on_darkness_slider_change(self, value=None) -> None:
        self._update_darkness_entry()
        self._save_settings()
        self._update_preview()

    def _on_darkness_entry_change(self, event=None) -> None:
        try:
            value = float(self.darkness_entry.get())
            value = max(0.5, min(3.0, value))
            self.darkness_var.set(value)
            self._update_darkness_entry()
            self._save_settings()
            self._update_preview()
        except ValueError:
            self._update_darkness_entry()

    def _update_darkness_entry(self) -> None:
        self.darkness_entry.delete(0, "end")
        self.darkness_entry.insert(0, f"{self.darkness_var.get():.2f}")

    def _on_calendar(self) -> None:
        # open calendar generator dialog
        CalendarDialog(
            self.winfo_toplevel(),
            on_insert_image=self._on_calendar_image
        )

    def _on_calendar_image(self, image: Image.Image) -> None:
        # set calendar image as template
        if image:
            self.set_template_image(image, "Calendar")

    def set_template_image(self, image: Image.Image, name: str = "Generated") -> None:
        # set template image directly from a pil image object
        self._io_manager.set_template_image(image, name)
        self._renderer.set_template(image)
        self.template_label.configure(
            text=name,
            text_color=("gray30", "gray70")
        )
        self._update_preview()

    def _on_template_loaded_callback(self, image: Image.Image, name: str) -> None:
        # callback from I/O manager when template is loaded
        self._renderer.set_template(image)
        self.template_label.configure(
            text=name,
            text_color=("gray30", "gray70")
        )
        self._update_preview()

    def _on_show_gallery(self) -> None:
        # show template gallery dialog
        TemplateGallery(
            self,
            templates_dir="gallery/templates",
            on_template_selected=self._on_gallery_template_selected
        )

    def _on_gallery_template_selected(self, filepath: str) -> None:
        # called when user selects template from gallery
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.pcfg':
            self._load_pcfg(filepath)
        else:
            self._load_template(filepath)

    def _load_pcfg(self, filepath: str) -> None:
        # load a saved label configuration file using I/O manager
        config = self._io_manager.load_pcfg(filepath)
        if config:
            # load text areas directly into manager
            if config.text_areas:
                # clear existing areas
                self._text_area_manager.delete_all()
                # add loaded areas
                for area in config.text_areas:
                    self._text_area_manager.add_area(area)

            # load darkness setting
            self.darkness_var.set(config.darkness)
            self._update_darkness_entry()

            self._update_preview()

    def _load_template(self, filepath: str) -> None:
        # load template image using I/O manager
        self._io_manager.load_template(filepath)

    def _on_clear_template(self) -> None:
        self._io_manager.clear_template()
        self._renderer.set_template(None)
        self.template_label.configure(
            text="No template loaded",
            text_color="gray"
        )
        # clear all text areas
        self._text_area_manager.delete_all()
        self.preview_canvas.clear()
        self._set_status("Template and areas cleared")

    def _update_preview(self) -> None:
        template_image = self._io_manager.template_image
        if not template_image:
            self.preview_canvas.clear()
            return

        try:
            # update all state at once - single redraw
            self.preview_canvas.update_state(
                image=template_image,
                text_areas=self._text_area_manager.text_areas,
                selected_index=self._text_area_manager.current_index,
                darkness=self.darkness_var.get()
            )
        except Exception as e:
            self._set_status(f"Preview error: {e}")

    def _on_save_label(self) -> None:
        # save current area first
        self._save_current_area_from_ui()

        filepath = save_file_dialog(
            title="Save Label Configuration",
            filetypes=[("All files", "*.*"), ("Printer config files", "*.pcfg")],
            defaultextension=".pcfg",
            initialdir="gallery/templates"
        )

        if not filepath:
            return

        # get rendered preview for thumbnail
        rendered = self.preview_canvas.get_rendered_preview()

        # use I/O manager to save
        self._io_manager.save_label(
            filepath=filepath,
            text_areas=self._text_area_manager.text_areas,
            darkness=self.darkness_var.get(),
            rendered_preview=rendered
        )

    def _on_print(self) -> None:
        template_image = self._io_manager.template_image
        if not template_image:
            self._set_status("No template loaded")
            return

        # save current area
        self._save_current_area_from_ui()

        try:
            # get rendered RGB image with text
            rgb_image = self._renderer.get_print_image(
                self._text_area_manager.text_areas,
                self.darkness_var.get()
            )
            if not rgb_image:
                self._set_status("Error: Could not render label")
                return

            # convert to 1-bit for thermal printing using ImageProcessor
            processor = ImageProcessor(
                brightness=1.0,
                contrast=1.0,
                dither_mode="floyd-steinberg",
                rotation=0,
                invert=False,
                auto_resize=True,
            )
            print_image = processor.process(rgb_image)

            # use printer service if available otherwise use legacy callback
            if self._printer_service:
                self._printer_service.print_image(print_image)
            elif self.on_print_request:
                self.on_print_request(print_image)
            self._set_status("Sending label to printer...")
        except Exception as e:
            self._set_status(f"Error preparing print: {e}")

    def _set_status(self, message: str) -> None:
        # use status service if available otherwise use legacy callback
        if self._status_service:
            self._status_service.set_status(message)
        elif self.on_status_change:
            self.on_status_change(message)

    def save(self) -> None:
        # public method to trigger save called by app for ctrl+s
        self._on_save_label()
