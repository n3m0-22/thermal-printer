# template gallery dialog for browsing and selecting label templates

from typing import Optional, Callable, List, Tuple, TYPE_CHECKING
import os
import json
from pathlib import Path
import customtkinter as ctk
from ...utils.pil_compat import Image, ImageDraw, PhotoImage, is_imagetk_available

if TYPE_CHECKING:
    from ...gui.interfaces import SettingsService

from .centered_dialog import CenteredDialog
from ...config.defaults import (
    SUPPORTED_IMAGE_FORMATS,
    DIALOG_GALLERY_MIN_WIDTH,
    DIALOG_GALLERY_MIN_HEIGHT,
    DIALOG_BUTTON_WIDTH,
    DIALOG_BUTTON_HEIGHT,
    DIALOG_BUTTON_LARGE_WIDTH,
    BUTTON_DELETE_FG,
    BUTTON_DELETE_HOVER,
    DEBOUNCE_SEARCH_MS,
    DOUBLE_CLICK_DELAY_MS,
    GALLERY_THUMBNAIL_BG,
    GALLERY_THUMBNAIL_BORDER,
    GALLERY_THUMBNAIL_TEXT,
    GALLERY_THUMBNAIL_LABEL_BG,
    GALLERY_THUMBNAIL_LABEL_TEXT,
    GALLERY_ERROR_THUMBNAIL_BG,
    GALLERY_ERROR_THUMBNAIL_BORDER,
    GALLERY_PCFG_THUMBNAIL_BG,
)
from ...config.keys import SettingsKeys
from ...config.settings import get_settings
from ...utils.file_dialogs import open_file_dialog
from ...utils.shortcuts import bind_entry_shortcuts
from ..theme import AppFonts

THUMBNAIL_SIZES = {
    "Small": 80,
    "Medium": 120,
    "Large": 160,
    "Extra Large": 220,
}
DEFAULT_THUMBNAIL_SIZE = "Medium"


class TemplateGallery(CenteredDialog):
    # popup dialog for browsing and selecting template images

    def __init__(
        self,
        master,
        templates_dir: str = "templates",
        on_template_selected: Optional[Callable[[str], None]] = None,
        settings_service: Optional["SettingsService"] = None,
        **kwargs
    ):
        self.on_template_selected = on_template_selected
        self.templates_dir = templates_dir
        self._settings = settings_service if settings_service else get_settings()

        self._templates: List[Tuple[str, str]] = []  # (filepath, name)
        self._filtered_templates: List[Tuple[str, str]] = []
        self._thumbnail_cache: dict = {}
        self._photo_cache: List[PhotoImage] = []  # keep references
        self._button_refs: dict = {}  # filepath -> button widget for selection updates
        self._selected_path: Optional[str] = None
        self._thumbnail_size_name = self._load_thumbnail_size()
        self._thumbnail_size = THUMBNAIL_SIZES[self._thumbnail_size_name]
        self._pending_click: Optional[str] = None

        # calculate dialog size based on parent window
        parent_toplevel = master.winfo_toplevel()
        parent_toplevel.update_idletasks()
        parent_width = parent_toplevel.winfo_width()
        parent_height = parent_toplevel.winfo_height()
        width = max(DIALOG_GALLERY_MIN_WIDTH, int(parent_width * 0.7))
        height = max(DIALOG_GALLERY_MIN_HEIGHT, int(parent_height * 0.8))

        super().__init__(
            master,
            title="Select Template",
            width=width,
            height=height,
            **kwargs
        )

        self.bind("<Escape>", lambda e: self._on_close())

    def _build_content(self) -> None:
        label_font = AppFonts.label()
        ctrl_font = AppFonts.control()
        btn_font = AppFonts.button()

        top_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        top_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            top_frame,
            text="Search:",
            font=label_font
        ).pack(side="left", padx=(0, 5))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)

        self.search_entry = ctk.CTkEntry(
            top_frame,
            textvariable=self._search_var,
            placeholder_text="Filter templates...",
            width=200,
            height=DIALOG_BUTTON_HEIGHT,
            font=ctrl_font
        )
        self.search_entry.pack(side="left", padx=(0, 20))

        bind_entry_shortcuts(self, self.search_entry)

        ctk.CTkLabel(
            top_frame,
            text="Size:",
            font=label_font
        ).pack(side="left", padx=(0, 5))

        self.size_selector = ctk.CTkOptionMenu(
            top_frame,
            values=list(THUMBNAIL_SIZES.keys()),
            width=DIALOG_BUTTON_WIDTH,
            height=DIALOG_BUTTON_HEIGHT,
            font=ctrl_font,
            command=self._on_size_change
        )
        self.size_selector.set(self._thumbnail_size_name)
        self.size_selector.pack(side="left", padx=(0, 20))

        self.load_custom_btn = ctk.CTkButton(
            top_frame,
            text="Load Custom...",
            width=DIALOG_BUTTON_LARGE_WIDTH,
            height=DIALOG_BUTTON_HEIGHT,
            font=btn_font,
            command=self._on_load_custom
        )
        self.load_custom_btn.pack(side="right")

        self.grid_frame = ctk.CTkScrollableFrame(self.content_frame)
        self.grid_frame.pack(fill="both", expand=True, pady=(0, 10))

        # bind mouse wheel to dialog (catches all events)
        canvas = self.grid_frame._parent_canvas
        self.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-3, "units"))
        self.bind_all("<Button-5>", lambda e: canvas.yview_scroll(3, "units"))

        # track width for resize detection
        self._last_dialog_width = 0
        self.bind("<Configure>", self._on_dialog_resize)

        button_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        button_frame.pack(fill="x")

        self.close_btn = ctk.CTkButton(
            button_frame,
            text="Close",
            width=DIALOG_BUTTON_WIDTH,
            height=DIALOG_BUTTON_HEIGHT,
            font=btn_font,
            command=self._on_close
        )
        self.close_btn.pack(side="left")

        self.delete_btn = ctk.CTkButton(
            button_frame,
            text="Delete",
            width=DIALOG_BUTTON_WIDTH,
            height=DIALOG_BUTTON_HEIGHT,
            font=btn_font,
            fg_color=BUTTON_DELETE_FG,
            hover_color=BUTTON_DELETE_HOVER,
            command=self._on_delete
        )
        self.delete_btn.pack(side="left", padx=(10, 0))

        self.select_btn = ctk.CTkButton(
            button_frame,
            text="Select",
            width=DIALOG_BUTTON_WIDTH,
            height=DIALOG_BUTTON_HEIGHT,
            font=btn_font,
            command=self._on_select
        )
        self.select_btn.pack(side="right")

        self.status_label = ctk.CTkLabel(
            button_frame,
            text="",
            font=ctrl_font,
            text_color="gray"
        )
        self.status_label.pack(side="left", padx=20)

        # load templates after ui built
        self._scan_templates()

    def _scan_templates(self) -> None:
        self._templates = []

        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(os.path.join(self.templates_dir, "thumbs"), exist_ok=True)

        if os.path.isdir(self.templates_dir):
            for filename in sorted(os.listdir(self.templates_dir)):
                filepath = os.path.join(self.templates_dir, filename)
                if self._is_template_file(filepath):
                    name = Path(filename).stem
                    self._templates.append((filepath, name))

        self._filtered_templates = self._templates.copy()
        self._update_status()
        self._populate_grid()

    def _is_template_file(self, filepath: str) -> bool:
        filename = Path(filepath).name
        # exclude auto-generated thumbnail files
        if filename.endswith('_thumb.png'):
            return False
        ext = Path(filepath).suffix.lower()
        return ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.pcfg', '.txt']

    def _on_search_change(self, *args) -> None:
        # debounce to avoid rebuilding grid on every keystroke
        if hasattr(self, '_search_pending'):
            self.after_cancel(self._search_pending)
        self._search_pending = self.after(DEBOUNCE_SEARCH_MS, self._do_search_update)

    def _do_search_update(self) -> None:
        search = self._search_var.get().lower()
        if search:
            self._filtered_templates = [
                (path, name) for path, name in self._templates
                if search in name.lower()
            ]
        else:
            self._filtered_templates = self._templates.copy()

        self._update_status()
        self._populate_grid()

    def _load_thumbnail_size(self) -> str:
        saved_size = self._settings.get(SettingsKeys.Gui.GALLERY_THUMBNAIL_SIZE, DEFAULT_THUMBNAIL_SIZE)
        if saved_size in THUMBNAIL_SIZES:
            return saved_size
        return DEFAULT_THUMBNAIL_SIZE

    def _save_thumbnail_size(self, size_name: str) -> None:
        self._settings.set(SettingsKeys.Gui.GALLERY_THUMBNAIL_SIZE, size_name)
        self._settings.save_immediate()

    def _on_size_change(self, value: str) -> None:
        self._thumbnail_size_name = value
        self._thumbnail_size = THUMBNAIL_SIZES.get(value, 120)
        self._save_thumbnail_size(value)
        self._thumbnail_cache.clear()
        self._populate_grid()

    def _update_status(self) -> None:
        total = len(self._templates)
        shown = len(self._filtered_templates)
        if total == shown:
            self.status_label.configure(text=f"{total} templates")
        else:
            self.status_label.configure(text=f"Showing {shown} of {total}")

    def _get_thumbnail(self, filepath: str) -> Optional[PhotoImage]:
        if not is_imagetk_available():
            return None

        cache_key = (filepath, self._thumbnail_size)

        if cache_key in self._thumbnail_cache:
            return self._thumbnail_cache[cache_key]

        try:
            ext = Path(filepath).suffix.lower()

            if ext == '.pcfg':
                img = self._get_pcfg_thumbnail(filepath)
            elif ext == '.txt':
                img = self._get_text_thumbnail(filepath)
            else:
                img = Image.open(filepath)

            if img is None:
                return None

            # calculate thumbnail size preserving aspect ratio
            width, height = img.size
            if width > height:
                new_width = self._thumbnail_size
                new_height = int(height * (self._thumbnail_size / width))
            else:
                new_height = self._thumbnail_size
                new_width = int(width * (self._thumbnail_size / height))

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            if img.mode != 'RGB':
                img = img.convert('RGB')

            photo = PhotoImage(img)
            self._thumbnail_cache[cache_key] = photo
            self._photo_cache.append(photo)
            return photo
        except Exception:
            return None

    def _get_text_thumbnail(self, filepath: str) -> Optional[Image.Image]:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read(200)

            size = self._thumbnail_size
            img = Image.new('RGB', (size, size), color='#FFFFFF')
            draw = ImageDraw.Draw(img)

            draw.rectangle([2, 2, size-3, size-3], outline='#CCCCCC', width=1)

            lines = content.split('\n')[:5]
            y = 8
            for line in lines:
                display_line = line[:20] + '...' if len(line) > 20 else line
                draw.text((8, y), display_line, fill='#333333')
                y += 14
                if y > size - 20:
                    break

            draw.rectangle([0, size-18, size, size], fill='#F0F0F0')
            draw.text((size//2, size-9), "TXT", fill='#666666', anchor='mm')
            return img
        except Exception:
            size = self._thumbnail_size
            img = Image.new('RGB', (size, size), color='#F5F5F5')
            draw = ImageDraw.Draw(img)
            draw.rectangle([4, 4, size-4, size-4], outline='#888888', width=2)
            draw.text((size//2, size//2), "TXT", fill='#666666', anchor='mm')
            return img

    def _get_pcfg_thumbnail(self, filepath: str) -> Optional[Image.Image]:
        # load rendered thumbnail from pcfg or fall back to template image
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = json.load(f)

            thumbnail_path = config.get('thumbnail_path', '')
            if thumbnail_path and os.path.isfile(thumbnail_path):
                return Image.open(thumbnail_path)

            parent_dir = os.path.dirname(filepath)
            base_name = os.path.splitext(os.path.basename(filepath))[0]
            thumbs_path = os.path.join(parent_dir, "thumbs", f"{base_name}_thumb.png")
            if os.path.isfile(thumbs_path):
                return Image.open(thumbs_path)

            template_path = config.get('template_path', '')
            if template_path and os.path.isfile(template_path):
                return Image.open(template_path)

            # fallback if no valid image found
            size = self._thumbnail_size
            img = Image.new('RGB', (size, size), color='#E0E0E0')
            draw = ImageDraw.Draw(img)
            draw.rectangle([4, 4, size-4, size-4], outline='#888888', width=2)
            draw.text((size//2, size//2), "PCFG", fill='#666666', anchor='mm')
            return img
        except Exception:
            return None

    def _on_dialog_resize(self, event) -> None:
        # only respond to width changes on the dialog itself
        if event.widget != self:
            return
        new_width = event.width
        if abs(new_width - self._last_dialog_width) > 50:
            self._last_dialog_width = new_width
            if hasattr(self, '_resize_pending'):
                self.after_cancel(self._resize_pending)
            self._resize_pending = self.after(150, self._populate_grid)

    def _populate_grid(self) -> None:
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        self._photo_cache.clear()
        self._button_refs.clear()

        # reset all column configurations
        for col in range(20):  # clear up to 20 columns
            self.grid_frame.grid_columnconfigure(col, weight=0, uniform="")

        if not self._filtered_templates:
            ctk.CTkLabel(
                self.grid_frame,
                text="No templates found",
                font=AppFonts.normal(),
                text_color="gray"
            ).grid(row=0, column=0, pady=50)
            return

        # calculate columns based on dialog width (grid_frame width is unreliable)
        self.update_idletasks()
        dialog_width = self.winfo_width()
        # account for dialog padding, scrollbar, and margins
        available_width = dialog_width - 60

        card_width = self._thumbnail_size + 30  # thumbnail + padding
        num_cols = max(1, available_width // card_width)
        self._last_dialog_width = dialog_width

        # configure grid columns to be uniform
        for col in range(num_cols):
            self.grid_frame.grid_columnconfigure(col, weight=1, uniform="card")

        # place cards in grid
        for idx, (filepath, name) in enumerate(self._filtered_templates):
            row = idx // num_cols
            col = idx % num_cols
            self._create_template_card(filepath, name, row, col)

        self.grid_frame.update_idletasks()

    def _create_template_card(self, filepath: str, name: str, row: int, col: int) -> None:
        card = ctk.CTkFrame(
            self.grid_frame,
            fg_color="transparent",
            corner_radius=8
        )
        card.grid(row=row, column=col, padx=5, pady=5, sticky="n")

        thumbnail = self._get_thumbnail(filepath)

        btn = ctk.CTkButton(
            card,
            image=thumbnail,
            text="",
            width=self._thumbnail_size + 10,
            height=self._thumbnail_size + 10,
            fg_color=("gray90", "gray20") if filepath != self._selected_path else ("gray70", "gray40"),
            hover_color=("gray80", "gray30"),
            corner_radius=8,
            command=lambda p=filepath: self._on_thumbnail_click(p)
        )
        btn.pack(padx=5, pady=(5, 2))

        self._button_refs[filepath] = btn

        dbl_click_handler = lambda e, p=filepath: self._on_thumbnail_double_click(p)
        btn.bind("<Double-Button-1>", dbl_click_handler)
        for child in btn.winfo_children():
            child.bind("<Double-Button-1>", dbl_click_handler)

        display_name = name[:15] + "..." if len(name) > 15 else name
        label = ctk.CTkLabel(
            card,
            text=display_name,
            font=AppFonts.small(),
            width=self._thumbnail_size
        )
        label.pack(pady=(0, 5))

    def _on_thumbnail_click(self, filepath: str) -> None:
        # delay to allow double-click detection
        self._pending_click = filepath
        self.after(DOUBLE_CLICK_DELAY_MS, lambda: self._process_pending_click(filepath))

    def _process_pending_click(self, filepath: str) -> None:
        if self._pending_click == filepath:
            old_selected = self._selected_path
            self._selected_path = filepath
            self._pending_click = None

            self._update_selection_visual(old_selected, filepath)

    def _update_selection_visual(
        self,
        old_path: Optional[str],
        new_path: Optional[str]
    ) -> None:
        if old_path and old_path in self._button_refs:
            try:
                self._button_refs[old_path].configure(
                    fg_color=("gray90", "gray20")
                )
            except Exception:
                pass

        if new_path and new_path in self._button_refs:
            try:
                self._button_refs[new_path].configure(
                    fg_color=("gray70", "gray40")
                )
            except Exception:
                pass

    def _on_thumbnail_double_click(self, filepath: str) -> None:
        self._pending_click = None
        self._selected_path = filepath
        self._on_select()

    def _on_load_custom(self) -> None:
        filetypes = [(name, pattern) for name, pattern in SUPPORTED_IMAGE_FORMATS]
        filepath = open_file_dialog(
            title="Load Custom Template",
            filetypes=filetypes
        )

        if filepath:
            self._selected_path = filepath
            self._on_select()

    def _on_select(self) -> None:
        if self._selected_path and self.on_template_selected:
            self.on_template_selected(self._selected_path)
        self._on_close()

    def _on_delete(self) -> None:
        if not self._selected_path:
            return

        filepath = self._selected_path
        filename = os.path.basename(filepath)

        try:
            if os.path.isfile(filepath):
                os.remove(filepath)

            base_path = os.path.splitext(filepath)[0]
            thumb_path = f"{base_path}_thumb.png"
            if os.path.isfile(thumb_path):
                os.remove(thumb_path)

            parent_dir = os.path.dirname(filepath)
            base_name = os.path.splitext(os.path.basename(filepath))[0]
            thumbs_path = os.path.join(parent_dir, "thumbs", f"{base_name}_thumb.png")
            if os.path.isfile(thumbs_path):
                os.remove(thumbs_path)

            self._selected_path = None
            self._thumbnail_cache.clear()
            self._scan_templates()
            self.status_label.configure(text=f"Deleted: {filename}")
        except Exception as e:
            self.status_label.configure(text=f"Error: {e}")
