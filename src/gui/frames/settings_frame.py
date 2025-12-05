# settings panel for application configuration

from typing import Optional, Callable, TYPE_CHECKING
import customtkinter as ctk

from ...config.defaults import (
    APPEARANCE_MODES,
    COLOR_THEMES,
    DEFAULT_APPEARANCE,
    DEFAULT_COLOR_THEME,
    DEFAULT_COMMAND_DELAY,
    DEFAULT_FEED_LINES_BEFORE,
    DEFAULT_FEED_LINES_AFTER,
    MIN_FEED_LINES,
    MAX_FEED_LINES,
    DATE_FORMATS,
    DEFAULT_DATE_FORMAT,
    DEFAULT_PREVIEW_SCALE,
    PREVIEW_MIN_SCALE,
    PREVIEW_MAX_SCALE,
    DEFAULT_UNICODE_FONT,
    RECOMMENDED_UNICODE_FONTS,
)
from ...utils.font_manager import get_font_manager
from ..widgets.font_selector import FontSelector
from ...config.keys import SettingsKeys
from ...config.settings import get_settings
from ..dialogs.about_dialog import AboutDialog

# service interfaces
if TYPE_CHECKING:
    from ..interfaces import StatusService, SettingsService
from ..interfaces import create_services_from_app


class SettingsFrame(ctk.CTkScrollableFrame):

    def __init__(
        self,
        master,
        on_status_change: Optional[Callable[[str], None]] = None,
        status_service: Optional["StatusService"] = None,
        settings_service: Optional["SettingsService"] = None,
        app=None,  # backward compatibility - accepts full app instance
        **kwargs
    ):
        super().__init__(master, **kwargs)

        # if services not provided but app is then create adapters
        if app is not None and (status_service is None or settings_service is None):
            _printer, _status, _settings, _conn = create_services_from_app(app)
            status_service = status_service or _status
            settings_service = settings_service or _settings

        self._status_service = status_service
        self._settings_service = settings_service
        self.on_status_change = on_status_change
        self._settings = settings_service if settings_service else get_settings()

        self._setup_ui()
        self._load_settings()
        self._bind_mouse_wheel()

    def _bind_mouse_wheel(self) -> None:
        def can_scroll(direction: int) -> bool:
            """Check if scrolling in the given direction is allowed."""
            top, bottom = self._parent_canvas.yview()
            if top == 0.0 and bottom == 1.0:
                return False
            if direction < 0:
                return top > 0.0
            else:
                return bottom < 1.0

        def _on_mousewheel(event):
            direction = -1 if event.delta > 0 else 1
            if can_scroll(direction):
                self._parent_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        def _on_mousewheel_linux(event):
            if event.num == 4:
                if can_scroll(-1):
                    self._parent_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                if can_scroll(1):
                    self._parent_canvas.yview_scroll(1, "units")
            return "break"

        self.bind("<MouseWheel>", _on_mousewheel)
        self.bind("<Button-4>", _on_mousewheel_linux)
        self.bind("<Button-5>", _on_mousewheel_linux)

        def bind_children(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            widget.bind("<Button-4>", _on_mousewheel_linux)
            widget.bind("<Button-5>", _on_mousewheel_linux)
            for child in widget.winfo_children():
                bind_children(child)

        self.after(100, lambda: bind_children(self))

    def _setup_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)

        title_font = ctk.CTkFont(size=20, weight="bold")
        section_font = ctk.CTkFont(size=16, weight="bold")
        label_font = ctk.CTkFont(size=14)
        btn_font = ctk.CTkFont(size=14)

        ctk.CTkLabel(
            self, text="Application Settings",
            font=title_font
        ).grid(row=0, column=0, columnspan=3, pady=(10, 20), padx=10, sticky="w")

        ctk.CTkLabel(
            self, text="Appearance",
            font=section_font
        ).grid(row=1, column=0, columnspan=3, pady=(10, 8), padx=10, sticky="w")

        ctk.CTkLabel(self, text="Mode:", font=label_font).grid(row=2, column=0, pady=6, padx=(20, 10), sticky="w")

        self.appearance_var = ctk.StringVar(value=DEFAULT_APPEARANCE)
        self.appearance_dropdown = ctk.CTkOptionMenu(
            self,
            values=APPEARANCE_MODES,
            variable=self.appearance_var,
            width=180, height=34,
            font=label_font,
            command=self._on_appearance_change
        )
        self.appearance_dropdown.grid(row=2, column=1, pady=8, padx=10, sticky="w")

        ctk.CTkLabel(self, text="Color Theme:", font=label_font).grid(row=3, column=0, pady=8, padx=(20, 10), sticky="w")

        self.theme_var = ctk.StringVar(value=DEFAULT_COLOR_THEME)
        self.theme_dropdown = ctk.CTkOptionMenu(
            self,
            values=COLOR_THEMES,
            variable=self.theme_var,
            width=180, height=34,
            font=label_font,
            command=self._on_theme_change
        )
        self.theme_dropdown.grid(row=3, column=1, pady=8, padx=10, sticky="w")

        ctk.CTkLabel(self, text="Preview Scale:", font=label_font).grid(row=4, column=0, pady=8, padx=(20, 10), sticky="w")

        self.preview_scale_var = ctk.DoubleVar(value=DEFAULT_PREVIEW_SCALE)
        self.preview_scale_slider = ctk.CTkSlider(
            self,
            from_=PREVIEW_MIN_SCALE,
            to=PREVIEW_MAX_SCALE,
            variable=self.preview_scale_var,
            width=200, height=20,
            command=self._on_preview_scale_slider_change
        )
        self.preview_scale_slider.grid(row=4, column=1, pady=8, padx=10, sticky="w")

        self.preview_scale_entry = ctk.CTkEntry(self, width=60, height=32, font=label_font)
        self.preview_scale_entry.grid(row=4, column=2, pady=8, padx=5, sticky="w")
        self.preview_scale_entry.insert(0, f"{DEFAULT_PREVIEW_SCALE:.2f}")
        self.preview_scale_entry.bind("<Return>", self._on_preview_scale_entry_change)
        self.preview_scale_entry.bind("<FocusOut>", self._on_preview_scale_entry_change)

        ctk.CTkLabel(
            self, text="Text Options",
            font=section_font
        ).grid(row=5, column=0, columnspan=3, pady=(20, 8), padx=10, sticky="w")

        ctk.CTkLabel(self, text="Date Format:", font=label_font).grid(row=6, column=0, pady=8, padx=(20, 10), sticky="w")

        self.date_format_var = ctk.StringVar(value=DEFAULT_DATE_FORMAT)
        self.date_format_dropdown = ctk.CTkOptionMenu(
            self,
            values=DATE_FORMATS,
            variable=self.date_format_var,
            width=220, height=34,
            font=label_font,
            command=self._on_date_format_change
        )
        self.date_format_dropdown.grid(row=6, column=1, pady=8, padx=10, sticky="w")

        ctk.CTkLabel(
            self, text="Timing",
            font=section_font
        ).grid(row=7, column=0, columnspan=3, pady=(20, 8), padx=10, sticky="w")

        ctk.CTkLabel(self, text="Command Delay (s):", font=label_font).grid(row=8, column=0, pady=8, padx=(20, 10), sticky="w")

        self.delay_var = ctk.DoubleVar(value=DEFAULT_COMMAND_DELAY)
        self.delay_slider = ctk.CTkSlider(
            self,
            from_=0.1,
            to=2.0,
            variable=self.delay_var,
            width=200, height=20,
            command=self._on_delay_slider_change
        )
        self.delay_slider.grid(row=8, column=1, pady=8, padx=10, sticky="w")

        self.delay_entry = ctk.CTkEntry(self, width=60, height=32, font=label_font)
        self.delay_entry.grid(row=8, column=2, pady=8, padx=5, sticky="w")
        self.delay_entry.insert(0, f"{DEFAULT_COMMAND_DELAY:.1f}")
        self.delay_entry.bind("<Return>", self._on_delay_entry_change)
        self.delay_entry.bind("<FocusOut>", self._on_delay_entry_change)

        ctk.CTkLabel(
            self, text="Printing",
            font=section_font
        ).grid(row=9, column=0, columnspan=3, pady=(20, 8), padx=10, sticky="w")

        ctk.CTkLabel(self, text="Feed Lines Before:", font=label_font).grid(row=10, column=0, pady=8, padx=(20, 10), sticky="w")

        self.feed_before_var = ctk.IntVar(value=DEFAULT_FEED_LINES_BEFORE)
        self.feed_before_slider = ctk.CTkSlider(
            self,
            from_=MIN_FEED_LINES,
            to=MAX_FEED_LINES,
            variable=self.feed_before_var,
            width=200, height=20,
            number_of_steps=MAX_FEED_LINES,
            command=self._on_feed_before_slider_change
        )
        self.feed_before_slider.grid(row=10, column=1, pady=8, padx=10, sticky="w")

        self.feed_before_entry = ctk.CTkEntry(self, width=50, height=32, font=label_font)
        self.feed_before_entry.grid(row=10, column=2, pady=8, padx=5, sticky="w")
        self.feed_before_entry.insert(0, str(DEFAULT_FEED_LINES_BEFORE))
        self.feed_before_entry.bind("<Return>", self._on_feed_before_entry_change)
        self.feed_before_entry.bind("<FocusOut>", self._on_feed_before_entry_change)

        ctk.CTkLabel(self, text="Feed Lines After:", font=label_font).grid(row=11, column=0, pady=8, padx=(20, 10), sticky="w")

        self.feed_after_var = ctk.IntVar(value=DEFAULT_FEED_LINES_AFTER)
        self.feed_after_slider = ctk.CTkSlider(
            self,
            from_=MIN_FEED_LINES,
            to=MAX_FEED_LINES,
            variable=self.feed_after_var,
            width=200, height=20,
            number_of_steps=MAX_FEED_LINES,
            command=self._on_feed_after_slider_change
        )
        self.feed_after_slider.grid(row=11, column=1, pady=8, padx=10, sticky="w")

        self.feed_after_entry = ctk.CTkEntry(self, width=50, height=32, font=label_font)
        self.feed_after_entry.grid(row=11, column=2, pady=8, padx=5, sticky="w")
        self.feed_after_entry.insert(0, str(DEFAULT_FEED_LINES_AFTER))
        self.feed_after_entry.bind("<Return>", self._on_feed_after_entry_change)
        self.feed_after_entry.bind("<FocusOut>", self._on_feed_after_entry_change)

        ctk.CTkLabel(
            self, text="Unicode",
            font=section_font
        ).grid(row=12, column=0, columnspan=3, pady=(20, 8), padx=10, sticky="w")

        self.unicode_popup_var = ctk.BooleanVar(value=True)
        self.unicode_popup_check = ctk.CTkCheckBox(
            self,
            text="Show popup when font is switched for Unicode support",
            variable=self.unicode_popup_var,
            font=label_font,
            command=self._on_unicode_popup_change
        )
        self.unicode_popup_check.grid(row=13, column=0, columnspan=2, pady=8, padx=(20, 10), sticky="w")

        # unicode font selector
        ctk.CTkLabel(
            self, text="Unicode Font:",
            font=label_font
        ).grid(row=14, column=0, pady=8, padx=(20, 10), sticky="w")

        font_manager = get_font_manager()
        self._font_families = font_manager.get_available_families()
        self.unicode_font_selector = FontSelector(
            self,
            fonts=self._font_families,
            command=self._on_unicode_font_change,
            width=220,
            height=32,
            recommended_fonts=RECOMMENDED_UNICODE_FONTS
        )
        self.unicode_font_selector.grid(row=14, column=1, pady=8, padx=10, sticky="w")

        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=15, column=0, columnspan=3, pady=(25, 10), padx=10, sticky="ew")

        ctk.CTkLabel(
            info_frame,
            text="Note: Some appearance changes may require restarting the application.",
            text_color=("gray40", "gray60"),
            font=ctk.CTkFont(size=14)
        ).pack(anchor="w")

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=16, column=0, columnspan=3, pady=10, padx=10, sticky="ew")

        self.reset_button = ctk.CTkButton(
            button_frame,
            text="Reset to Defaults",
            width=140, height=38,
            font=btn_font,
            command=self._on_reset
        )
        self.reset_button.pack(side="left")

        self.about_button = ctk.CTkButton(
            button_frame,
            text="About",
            width=100, height=38,
            font=btn_font,
            command=self._on_about
        )
        self.about_button.pack(side="left", expand=True)

        self.save_button = ctk.CTkButton(
            button_frame,
            text="Save Settings",
            width=140, height=38,
            font=btn_font,
            command=self._on_save
        )
        self.save_button.pack(side="right")

    def _load_settings(self) -> None:
        self.appearance_var.set(self._settings.get(SettingsKeys.Gui.APPEARANCE_MODE, DEFAULT_APPEARANCE))
        self.theme_var.set(self._settings.get(SettingsKeys.Gui.COLOR_THEME, DEFAULT_COLOR_THEME))
        self.preview_scale_var.set(self._settings.get(SettingsKeys.Gui.PREVIEW_SCALE, DEFAULT_PREVIEW_SCALE))
        self.delay_var.set(self._settings.get(SettingsKeys.Timing.COMMAND_DELAY, DEFAULT_COMMAND_DELAY))
        self.feed_before_var.set(self._settings.get(SettingsKeys.Printing.FEED_LINES_BEFORE, DEFAULT_FEED_LINES_BEFORE))
        self.feed_after_var.set(self._settings.get(SettingsKeys.Printing.FEED_LINES_AFTER, DEFAULT_FEED_LINES_AFTER))
        self.date_format_var.set(self._settings.get(SettingsKeys.Text.DATE_FORMAT, DEFAULT_DATE_FORMAT))
        self.unicode_popup_var.set(self._settings.get(SettingsKeys.Unicode.SHOW_FONT_SWITCH_POPUP, True))
        saved_unicode_font = self._settings.get(SettingsKeys.Unicode.PREFERRED_FONT, DEFAULT_UNICODE_FONT)
        if saved_unicode_font in self._font_families:
            self.unicode_font_selector.set(saved_unicode_font)
        else:
            self.unicode_font_selector.set(DEFAULT_UNICODE_FONT)

        self._update_delay_entry()
        self._update_feed_entries()
        self._update_preview_scale_entry()
        self._apply_appearance()

    def _save_settings(self) -> None:
        self._settings.set(SettingsKeys.Gui.APPEARANCE_MODE, self.appearance_var.get())
        self._settings.set(SettingsKeys.Gui.COLOR_THEME, self.theme_var.get())
        self._settings.set(SettingsKeys.Gui.PREVIEW_SCALE, round(self.preview_scale_var.get(), 2))
        self._settings.set(SettingsKeys.Timing.COMMAND_DELAY, round(self.delay_var.get(), 1))
        self._settings.set(SettingsKeys.Printing.FEED_LINES_BEFORE, int(self.feed_before_var.get()))
        self._settings.set(SettingsKeys.Printing.FEED_LINES_AFTER, int(self.feed_after_var.get()))
        self._settings.set(SettingsKeys.Text.DATE_FORMAT, self.date_format_var.get())
        self._settings.set(SettingsKeys.Unicode.SHOW_FONT_SWITCH_POPUP, self.unicode_popup_var.get())
        self._settings.set(SettingsKeys.Unicode.PREFERRED_FONT, self.unicode_font_selector.get())
        self._settings.save()

    def _on_appearance_change(self, value=None) -> None:
        self._apply_appearance()
        self._save_settings()
        self._set_status(f"Appearance mode: {self.appearance_var.get()}")

    def _on_theme_change(self, value=None) -> None:
        ctk.set_default_color_theme(self.theme_var.get())
        self._save_settings()
        self._set_status("Color theme changed (restart may be required)")

    def _on_preview_scale_slider_change(self, value=None) -> None:
        val = round(self.preview_scale_var.get(), 2)
        self.preview_scale_entry.delete(0, "end")
        self.preview_scale_entry.insert(0, f"{val:.2f}")
        self._save_settings()
        self._set_status(f"Preview scale: {val:.2f}x")

    def _on_preview_scale_entry_change(self, event=None) -> None:
        try:
            val = float(self.preview_scale_entry.get())
            val = max(PREVIEW_MIN_SCALE, min(PREVIEW_MAX_SCALE, val))
            val = round(val, 2)
            self.preview_scale_var.set(val)
            self.preview_scale_entry.delete(0, "end")
            self.preview_scale_entry.insert(0, f"{val:.2f}")
            self._save_settings()
            self._set_status(f"Preview scale: {val:.2f}x")
        except ValueError:
            self.preview_scale_entry.delete(0, "end")
            self.preview_scale_entry.insert(0, f"{self.preview_scale_var.get():.2f}")

    def _update_preview_scale_entry(self) -> None:
        self.preview_scale_entry.delete(0, "end")
        self.preview_scale_entry.insert(0, f"{self.preview_scale_var.get():.2f}")

    def _on_date_format_change(self, value=None) -> None:
        self._save_settings()
        self._set_status(f"Date format: {self.date_format_var.get()}")

    def _on_delay_slider_change(self, value=None) -> None:
        val = round(self.delay_var.get(), 1)
        self.delay_entry.delete(0, "end")
        self.delay_entry.insert(0, f"{val:.1f}")
        self._save_settings()

    def _on_delay_entry_change(self, event=None) -> None:
        try:
            val = float(self.delay_entry.get())
            val = max(0.1, min(2.0, val))
            self.delay_var.set(val)
            self.delay_entry.delete(0, "end")
            self.delay_entry.insert(0, f"{val:.1f}")
            self._save_settings()
        except ValueError:
            self.delay_entry.delete(0, "end")
            self.delay_entry.insert(0, f"{self.delay_var.get():.1f}")

    def _update_delay_entry(self) -> None:
        self.delay_entry.delete(0, "end")
        self.delay_entry.insert(0, f"{self.delay_var.get():.1f}")

    def _on_feed_before_slider_change(self, value=None) -> None:
        val = int(self.feed_before_var.get())
        self.feed_before_entry.delete(0, "end")
        self.feed_before_entry.insert(0, str(val))
        self._save_settings()

    def _on_feed_before_entry_change(self, event=None) -> None:
        try:
            val = int(self.feed_before_entry.get())
            val = max(MIN_FEED_LINES, min(MAX_FEED_LINES, val))
            self.feed_before_var.set(val)
            self.feed_before_entry.delete(0, "end")
            self.feed_before_entry.insert(0, str(val))
            self._save_settings()
        except ValueError:
            self.feed_before_entry.delete(0, "end")
            self.feed_before_entry.insert(0, str(int(self.feed_before_var.get())))

    def _on_feed_after_slider_change(self, value=None) -> None:
        val = int(self.feed_after_var.get())
        self.feed_after_entry.delete(0, "end")
        self.feed_after_entry.insert(0, str(val))
        self._save_settings()

    def _on_feed_after_entry_change(self, event=None) -> None:
        try:
            val = int(self.feed_after_entry.get())
            val = max(MIN_FEED_LINES, min(MAX_FEED_LINES, val))
            self.feed_after_var.set(val)
            self.feed_after_entry.delete(0, "end")
            self.feed_after_entry.insert(0, str(val))
            self._save_settings()
        except ValueError:
            self.feed_after_entry.delete(0, "end")
            self.feed_after_entry.insert(0, str(int(self.feed_after_var.get())))

    def _update_feed_entries(self) -> None:
        self.feed_before_entry.delete(0, "end")
        self.feed_before_entry.insert(0, str(int(self.feed_before_var.get())))
        self.feed_after_entry.delete(0, "end")
        self.feed_after_entry.insert(0, str(int(self.feed_after_var.get())))

    def _apply_appearance(self) -> None:
        mode = self.appearance_var.get()
        ctk.set_appearance_mode(mode)

    def _on_reset(self) -> None:
        self.appearance_var.set(DEFAULT_APPEARANCE)
        self.theme_var.set(DEFAULT_COLOR_THEME)
        self.preview_scale_var.set(DEFAULT_PREVIEW_SCALE)
        self.delay_var.set(DEFAULT_COMMAND_DELAY)
        self.feed_before_var.set(DEFAULT_FEED_LINES_BEFORE)
        self.feed_after_var.set(DEFAULT_FEED_LINES_AFTER)
        self.date_format_var.set(DEFAULT_DATE_FORMAT)
        self.unicode_popup_var.set(True)
        self.unicode_font_selector.set(DEFAULT_UNICODE_FONT)

        self._update_delay_entry()
        self._update_feed_entries()
        self._update_preview_scale_entry()
        self._apply_appearance()
        self._save_settings()

        self._set_status("Settings reset to defaults")

    def _on_unicode_popup_change(self) -> None:
        self._save_settings()
        state = "enabled" if self.unicode_popup_var.get() else "disabled"
        self._set_status(f"Unicode font switch popup {state}")

    def _on_unicode_font_change(self, font_name: str) -> None:
        """Called when unicode font is selected from FontSelector."""
        self._save_settings()
        self._set_status(f"Unicode font set to: {font_name}")

    def _on_about(self) -> None:
        dialog = AboutDialog(self.winfo_toplevel())
        dialog.focus()

    def _on_save(self) -> None:
        self._save_settings()
        self._set_status("Settings saved")

    def _set_status(self, message: str) -> None:
        if self._status_service:
            self._status_service.set_status(message)
        elif self.on_status_change:
            self.on_status_change(message)

    def get_command_delay(self) -> float:
        return self.delay_var.get()

    def get_feed_lines_before(self) -> int:
        return int(self.feed_before_var.get())

    def get_feed_lines_after(self) -> int:
        return int(self.feed_after_var.get())
