# main application window

from typing import Optional, Any
import logging
import customtkinter as ctk
from PIL import Image

logger = logging.getLogger(__name__)

from ..config.defaults import (
    APP_NAME,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    DEFAULT_APPEARANCE,
    DEFAULT_COLOR_THEME,
)
from ..config.keys import SettingsKeys
from ..config.settings import SettingsFactory
from ..core.printer import PrinterConnection, ConnectionState
from ..core.print_job import PrintJobConfig
from ..core.exceptions import NotConnectedError

from .frames.status_bar import StatusBar
from .frames.connection_frame import ConnectionFrame
from .frames.text_frame import TextFrame
from .frames.image_frame import ImageFrame
from .frames.banner_frame import BannerFrame
from .frames.template_frame import TemplateFrame
from .frames.settings_frame import SettingsFrame
from .dialogs.printer_scanner import PrinterScannerDialog
from .dialogs.message_dialog import show_error, show_warning, ask_yes_no
from ..utils.bluetooth import is_bluetooth_enabled, enable_bluetooth
from .app_components import TabManager, PrintCoordinator, FrameFactory


class PrinterApp(ctk.CTk):
    # tabbed interface for text and image printing

    def __init__(self) -> None:
        super().__init__()

        # hide during setup to prevent flash
        self.withdraw()

        self._settings = SettingsFactory.create()
        self._printer = PrinterConnection()

        # component factories
        self._frame_factory = FrameFactory(
            settings_service=self._settings,
            printer_service=self._printer,
            on_print_request=self._print_image,
            on_status_change=self._set_status,
            on_scan_request=self._show_scanner_dialog,
            on_bluetooth_check=self._ensure_bluetooth_enabled,
        )

        self._print_coordinator: Optional[PrintCoordinator] = None
        self._tab_manager: Optional[TabManager] = None

        self._setup_appearance()
        self._setup_window()
        self._setup_ui()
        self._setup_bindings()

        self._printer.add_state_callback(self._on_connection_state_change)

        # show window
        self.deiconify()

    def _on_print_progress(self, percentage: int, message: str) -> None:
        # schedule on main thread
        self.after(0, lambda: self.status_bar.set_progress_value(percentage, message))

    def _on_connection_lost(self) -> None:
        self.after(0, lambda: self.status_bar.set_connection_state(ConnectionState.ERROR))

    def _setup_appearance(self) -> None:
        appearance = self._settings.get(SettingsKeys.Gui.APPEARANCE_MODE, DEFAULT_APPEARANCE)
        theme = self._settings.get(SettingsKeys.Gui.COLOR_THEME, DEFAULT_COLOR_THEME)

        ctk.set_appearance_mode(appearance)
        ctk.set_default_color_theme(theme)

    def _setup_window(self) -> None:
        self.title(APP_NAME)
        self.tk.call('wm', 'iconname', self._w, 'thermal-printer')

        width = self._settings.get(SettingsKeys.Gui.WINDOW_WIDTH, DEFAULT_WINDOW_WIDTH)
        height = self._settings.get(SettingsKeys.Gui.WINDOW_HEIGHT, DEFAULT_WINDOW_HEIGHT)
        x = self._settings.get(SettingsKeys.Gui.WINDOW_X, None)
        y = self._settings.get(SettingsKeys.Gui.WINDOW_Y, None)

        self.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        if x is not None and y is not None:
            self.geometry(f"{width}x{height}+{x}+{y}")
        else:
            # update_idletasks required for accurate dimensions
            self.update_idletasks()
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            self.geometry(f"{width}x{height}+{x}+{y}")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

    def _setup_ui(self) -> None:
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=2, column=0, sticky="ew")

        self.connection_frame = ConnectionFrame(
            self,
            printer=self._printer,
            on_scan_request=self._show_scanner_dialog,
            on_status_change=self._set_status,
            on_bluetooth_check=self._ensure_bluetooth_enabled,
            settings_service=self._settings
        )
        self.connection_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        self.tabview = ctk.CTkTabview(self, command=self._on_tab_change)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        self.tabview.add("Text")
        self.tabview.add("Banner")
        self.tabview.add("Template")
        self.tabview.add("Image")
        self.tabview.add("Settings")

        frame_classes = {
            "Text": TextFrame,
            "Banner": BannerFrame,
            "Template": TemplateFrame,
            "Image": ImageFrame,
            "Settings": SettingsFrame,
        }
        self._tab_manager = TabManager(
            frame_classes=frame_classes,
            tabview=self.tabview,
            frame_factory=self._frame_factory,
        )

        from ..core.print_job import PrintJobManager
        self._print_manager = PrintJobManager(self._printer)
        self._print_coordinator = PrintCoordinator(
            print_manager=self._print_manager,
            on_progress=self._on_print_progress,
            on_complete=self._on_print_complete,
            on_connection_lost=self._on_connection_lost,
        )

        last_tab = self._get_last_tab()
        self.tabview.set(last_tab)

        try:
            seg_btn = self.tabview._segmented_button
            seg_btn.configure(
                font=ctk.CTkFont(size=14, weight="bold"),
                height=40,
                corner_radius=8
            )
            for btn in seg_btn._buttons_dict.values():
                btn.configure(width=100)
        except (AttributeError, KeyError) as e:
            logger.debug(f"Could not configure tab buttons: {e}")

        for tab_name in ["Text", "Banner", "Template", "Image", "Settings"]:
            self.tabview.tab(tab_name).grid_columnconfigure(0, weight=1)
            self.tabview.tab(tab_name).grid_rowconfigure(0, weight=1)

        self._tab_manager.ensure_frame_loaded(last_tab)

    def _on_tab_change(self) -> None:
        if self._tab_manager:
            self._tab_manager.on_tab_change()

    def _get_last_tab(self) -> str:
        last_tab = self._settings.get(SettingsKeys.Gui.LAST_TAB, "Text")
        valid_tabs = ["Text", "Banner", "Template", "Image", "Settings"]
        if last_tab in valid_tabs:
            return last_tab
        return "Text"

    def _save_last_tab(self) -> None:
        current_tab = self.tabview.get()
        self._settings.set(SettingsKeys.Gui.LAST_TAB, current_tab)

    # frame accessors
    @property
    def text_frame(self) -> TextFrame:
        return self._tab_manager.get_frame("Text")

    @property
    def banner_frame(self) -> BannerFrame:
        return self._tab_manager.get_frame("Banner")

    @property
    def template_frame(self) -> TemplateFrame:
        return self._tab_manager.get_frame("Template")

    @property
    def image_frame(self) -> ImageFrame:
        return self._tab_manager.get_frame("Image")

    @property
    def settings_frame(self) -> SettingsFrame:
        return self._tab_manager.get_frame("Settings")

    def _setup_bindings(self) -> None:
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.bind("<Configure>", self._on_resize)
        self.bind("<Control-s>", self._on_save_shortcut)
        self.bind("<Control-S>", self._on_save_shortcut)

    def _on_save_shortcut(self, event: Optional[Any] = None) -> str:
        current_tab = self.tabview.get()
        if current_tab == "Text" and hasattr(self.text_frame, 'save'):
            self.text_frame.save()
        elif current_tab == "Banner" and hasattr(self.banner_frame, 'save'):
            self.banner_frame.save()
        elif current_tab == "Template" and hasattr(self.template_frame, 'save'):
            self.template_frame.save()
        elif current_tab == "Image" and hasattr(self.image_frame, 'save'):
            self.image_frame.save()
        return "break"

    def _ensure_bluetooth_enabled(self) -> bool:
        if is_bluetooth_enabled():
            return True

        # prompt to enable bluetooth
        result = ask_yes_no(
            self,
            "Bluetooth Disabled",
            "Bluetooth is currently turned off.\n\n"
            "Would you like to enable Bluetooth?",
            icon="question",
            yes_text="Enable",
            no_text="Cancel"
        )

        if not result:
            return False

        self._set_status("Enabling Bluetooth...")
        self.update()

        if enable_bluetooth():
            self._set_status("Bluetooth enabled")
            return True
        else:
            show_warning(
                self,
                "Could Not Enable Bluetooth",
                "Failed to enable Bluetooth automatically.\n\n"
                "Please enable Bluetooth manually in your system settings."
            )
            self._set_status("Failed to enable Bluetooth")
            return False

    def _show_scanner_dialog(self) -> None:
        if not self._ensure_bluetooth_enabled():
            return

        dialog = PrinterScannerDialog(
            self,
            on_device_selected=self._on_device_selected
        )
        dialog.focus()

    def _on_device_selected(self, device: Any) -> None:
        self.connection_frame.set_device(device)
        self._set_status(f"Selected: {device.name} ({device.mac_address})")

    def _on_connection_state_change(self, state: ConnectionState) -> None:
        pass

    def _try_auto_connect(self) -> bool:
        if not self._ensure_bluetooth_enabled():
            return False

        mac_address = self._settings.get(SettingsKeys.Printer.MAC_ADDRESS, "")
        device_name = self._settings.get(SettingsKeys.Printer.DEVICE_NAME, "")

        if not mac_address:
            show_error(
                self,
                "Not Connected",
                "No printer configured.\n\n"
                "Please click 'Scan' to find your printer,\n"
                "or enter the MAC address manually."
            )
            return False

        self._set_status(f"Connecting to {device_name or mac_address}...")
        self.update()

        try:
            self._printer.connect(mac_address, device_name)
            return True
        except (ConnectionError, OSError) as e:
            show_error(
                self,
                "Connection Failed",
                f"Could not connect to printer:\n{e}\n\n"
                "Make sure the printer is:\n"
                "- Turned on\n"
                "- In range\n"
                "- Not connected to another device"
            )
            self._set_status("Connection failed")
            return False

    def _print_image(self, image: Image.Image) -> None:
        if self._print_coordinator.is_printing:
            self._set_status("Already printing, please wait...")
            return

        if not self._printer.is_connected:
            if self._try_auto_connect():
                self._set_status("Auto-connected to printer")
            else:
                return

        config = PrintJobConfig(
            feed_before=self.settings_frame.get_feed_lines_before(),
            feed_after=self.settings_frame.get_feed_lines_after(),
            command_delay=self.settings_frame.get_command_delay()
        )

        self._set_printing_ui_state(True)

        try:
            self._print_coordinator.print_image(image, config)
        except NotConnectedError:
            self._on_print_complete(False, "Error: Not connected to printer")

    def _cancel_current_print(self) -> None:
        if self._print_coordinator.cancel_print():
            self._set_status("Cancelling print...")

    def _set_printing_ui_state(self, printing: bool) -> None:
        state = "disabled" if printing else "normal"

        loaded_frames = self._tab_manager.get_loaded_frames()
        for tab_name in ["Text", "Image", "Banner", "Template"]:
            if tab_name in loaded_frames:
                frame = loaded_frames[tab_name]
                if hasattr(frame, 'print_button'):
                    frame.print_button.configure(state=state)

        if printing:
            self.status_bar.show_progress(True, self._cancel_current_print)
        else:
            self.status_bar.show_progress(False)

    def _on_print_complete(self, success: bool, message: str) -> None:
        self._set_printing_ui_state(False)
        self._set_status(message)

    def _set_status(self, message: str) -> None:
        self.status_bar.set_status(message)

    def _on_resize(self, event: Any) -> None:
        if event.widget == self:
            if hasattr(self, '_resize_after_id'):
                self.after_cancel(self._resize_after_id)
            self._resize_after_id = self.after(500, self._save_window_size)

    def _save_window_size(self) -> None:
        self._settings.set(SettingsKeys.Gui.WINDOW_WIDTH, self.winfo_width())
        self._settings.set(SettingsKeys.Gui.WINDOW_HEIGHT, self.winfo_height())
        self._settings.set(SettingsKeys.Gui.WINDOW_X, self.winfo_x())
        self._settings.set(SettingsKeys.Gui.WINDOW_Y, self.winfo_y())
        self._settings.save()

    def _on_closing(self) -> None:
        if self._printer.is_connected:
            try:
                self._printer.disconnect()
            except (OSError, ConnectionError) as e:
                logger.debug(f"Error disconnecting on close: {e}")

        try:
            self._save_last_tab()
            self._settings.save_immediate()
        except (OSError, IOError) as e:
            logger.warning(f"Could not save settings on close: {e}")

        self.destroy()


def run_app() -> None:
    app = PrinterApp()
    app.mainloop()
