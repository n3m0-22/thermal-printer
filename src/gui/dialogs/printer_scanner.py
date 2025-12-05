# bluetooth printer scanner

from typing import Optional, Callable, List, TYPE_CHECKING
import threading
import customtkinter as ctk

if TYPE_CHECKING:
    from ...gui.interfaces import SettingsService

from .centered_dialog import CenteredDialog
from ...core.printer import PrinterConnection, BluetoothDevice
from ...core.exceptions import ScanError
from ...config.keys import SettingsKeys
from ...config.settings import get_settings
from ...config.defaults import (
    DIALOG_SCANNER_WIDTH,
    DIALOG_SCANNER_HEIGHT,
    DIALOG_BUTTON_WIDTH,
    DIALOG_BUTTON_SMALL_WIDTH,
    BUTTON_CONNECT_FG,
    BUTTON_SCAN_FG,
    SCAN_START_DELAY_MS,
    SCROLL_BIND_DELAY_MS,
)
from ..theme import AppFonts


class PrinterScannerDialog(CenteredDialog):
    # scans nearby bluetooth and highlights ctp printers

    def __init__(
        self,
        master,
        on_device_selected: Optional[Callable[[BluetoothDevice], None]] = None,
        settings_service: Optional["SettingsService"] = None,
        **kwargs
    ):
        self.on_device_selected = on_device_selected
        self._settings = settings_service if settings_service is not None else get_settings()
        self._devices: List[BluetoothDevice] = []
        self._scanning = False
        self._selected_device: Optional[BluetoothDevice] = None

        super().__init__(
            master,
            title="Scan for Printers",
            width=DIALOG_SCANNER_WIDTH,
            height=DIALOG_SCANNER_HEIGHT,
            **kwargs
        )

        # auto start scan after dialog shown
        self.after(SCAN_START_DELAY_MS, self._start_scan)

    def _build_content(self) -> None:
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        title = ctk.CTkLabel(
            header_frame,
            text="Available Bluetooth Devices",
            font=AppFonts.label()
        )
        title.pack(side="left")

        self.scan_button = ctk.CTkButton(
            header_frame,
            text="Rescan",
            width=DIALOG_BUTTON_SMALL_WIDTH,
            command=self._start_scan
        )
        self.scan_button.pack(side="right")

        self.progress_label = ctk.CTkLabel(
            header_frame,
            text="",
            text_color="gray",
            font=AppFonts.normal()
        )
        self.progress_label.pack(side="right", padx=10)

        list_frame = ctk.CTkFrame(self.content_frame)
        list_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        self.device_scroll = ctk.CTkScrollableFrame(
            list_frame,
            fg_color="transparent"
        )
        self.device_scroll.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.device_scroll.grid_columnconfigure(0, weight=1)

        self.placeholder = ctk.CTkLabel(
            self.device_scroll,
            text="Scanning for devices...",
            text_color="gray",
            font=AppFonts.large()
        )
        self.placeholder.grid(row=0, column=0, pady=20)

        self._bind_scroll(self.device_scroll)

        info_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        info_frame.grid(row=2, column=0, sticky="ew", pady=5)

        info_label = ctk.CTkLabel(
            info_frame,
            text="CTP printers appear as 'CorePrint-XXXX' and are highlighted.",
            text_color="gray",
            font=AppFonts.normal()
        )
        info_label.pack(anchor="w")

        button_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        button_frame.grid(row=3, column=0, sticky="ew", pady=(5, 0))

        self.close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            width=DIALOG_BUTTON_WIDTH,
            command=self._on_close
        )
        self.close_button.pack(side="left")

        self.select_button = ctk.CTkButton(
            button_frame,
            text="Select",
            width=DIALOG_BUTTON_WIDTH,
            state="disabled",
            command=self._on_select
        )
        self.select_button.pack(side="right")

    def _start_scan(self) -> None:
        if self._scanning:
            return

        self._scanning = True
        self._devices = []
        self._selected_device = None

        self.scan_button.configure(state="disabled")
        self.select_button.configure(state="disabled")
        self.progress_label.configure(text="Scanning...")

        for widget in self.device_scroll.winfo_children():
            widget.destroy()

        self.placeholder = ctk.CTkLabel(
            self.device_scroll,
            text="Scanning for devices...",
            text_color="gray",
            font=AppFonts.large()
        )
        self.placeholder.grid(row=0, column=0, pady=20)

        scan_timeout = self._settings.get(SettingsKeys.Timing.SCAN_TIMEOUT, 10)

        def scan_thread():
            # thread to avoid blocking ui during bluetooth scan
            try:
                devices = PrinterConnection.scan_for_printers(timeout=scan_timeout)
                self.after(0, lambda: self._on_scan_complete(devices))
            except ScanError as e:
                self.after(0, lambda: self._on_scan_error(str(e)))
            except Exception as e:
                self.after(0, lambda: self._on_scan_error(str(e)))

        thread = threading.Thread(target=scan_thread, daemon=True)
        thread.start()

    def _on_scan_complete(self, devices: List[BluetoothDevice]) -> None:
        self._scanning = False
        self._devices = devices

        self.scan_button.configure(state="normal")
        self.progress_label.configure(text=f"Found {len(devices)} device(s)")

        for widget in self.device_scroll.winfo_children():
            widget.destroy()

        if not devices:
            no_devices = ctk.CTkLabel(
                self.device_scroll,
                text="No devices found.\nMake sure Bluetooth is enabled and the printer is on.",
                text_color="gray",
                justify="center"
            )
            no_devices.grid(row=0, column=0, pady=20)
            return

        for idx, device in enumerate(devices):
            self._create_device_entry(idx, device)

        # rebind scroll handlers after creating new widgets
        if hasattr(self, '_scroll_bind_func'):
            self.after(SCROLL_BIND_DELAY_MS, lambda: self._scroll_bind_func(self.device_scroll))

    def _on_scan_error(self, error: str) -> None:
        self._scanning = False
        self.scan_button.configure(state="normal")
        self.progress_label.configure(text="Scan failed")

        for widget in self.device_scroll.winfo_children():
            widget.destroy()

        error_label = ctk.CTkLabel(
            self.device_scroll,
            text=f"Scan error: {error}",
            text_color="red"
        )
        error_label.grid(row=0, column=0, pady=20)

    def _create_device_entry(self, index: int, device: BluetoothDevice) -> None:
        if device.is_ctp_printer:
            fg_color = BUTTON_CONNECT_FG
            text_color = ("white", "white")
            indicator = "[CTP]"
        else:
            fg_color = ("gray90", "gray20")
            text_color = ("gray10", "gray90")
            indicator = ""

        device_frame = ctk.CTkFrame(
            self.device_scroll,
            fg_color=fg_color,
            corner_radius=5
        )
        device_frame.grid(row=index, column=0, sticky="ew", pady=2, padx=2)
        device_frame.grid_columnconfigure(1, weight=1)

        device_frame.bind("<Button-1>", lambda e, d=device: self._select_device(d))

        radio_var = ctk.StringVar(value="")
        radio = ctk.CTkRadioButton(
            device_frame,
            text="",
            variable=radio_var,
            value=device.mac_address,
            width=20,
            fg_color=BUTTON_SCAN_FG,
            command=lambda d=device: self._select_device(d)
        )
        radio.grid(row=0, column=0, rowspan=2, padx=5, pady=5)
        # store widget refs for selection sync
        device_frame._radio = radio
        device_frame._radio_var = radio_var

        name_text = f"{device.name} {indicator}"
        name_label = ctk.CTkLabel(
            device_frame,
            text=name_text,
            font=ctk.CTkFont(weight="bold"),
            text_color=text_color,
            anchor="w"
        )
        name_label.grid(row=0, column=1, sticky="w", padx=5, pady=(5, 0))
        name_label.bind("<Button-1>", lambda e, d=device: self._select_device(d))

        mac_label = ctk.CTkLabel(
            device_frame,
            text=device.mac_address,
            text_color=("gray50", "gray60"),
            font=AppFonts.small(),
            anchor="w"
        )
        mac_label.grid(row=1, column=1, sticky="w", padx=5, pady=(0, 5))
        mac_label.bind("<Button-1>", lambda e, d=device: self._select_device(d))

    def _select_device(self, device: BluetoothDevice) -> None:
        self._selected_device = device
        self.select_button.configure(state="normal")

        # sync all radio buttons to selected device
        for widget in self.device_scroll.winfo_children():
            if hasattr(widget, '_radio_var'):
                if hasattr(widget, '_radio'):
                    widget._radio_var.set(device.mac_address)

    def _on_select(self) -> None:
        if self._selected_device and self.on_device_selected:
            self.on_device_selected(self._selected_device)
        self.destroy()

    def _bind_scroll(self, scrollable_frame) -> None:
        canvas = scrollable_frame._parent_canvas

        def can_scroll(direction: int) -> bool:
            """Check if scrolling in the given direction is allowed."""
            top, bottom = canvas.yview()
            if top == 0.0 and bottom == 1.0:
                return False
            if direction < 0:
                return top > 0.0
            else:
                return bottom < 1.0

        def on_mousewheel(event):
            direction = -1 if event.delta > 0 else 1
            if can_scroll(direction):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        def on_mousewheel_linux(event):
            if event.num == 4:
                if can_scroll(-1):
                    canvas.yview_scroll(-3, "units")
            elif event.num == 5:
                if can_scroll(1):
                    canvas.yview_scroll(3, "units")
            return "break"

        def bind_to_widget(widget):
            widget.bind("<MouseWheel>", on_mousewheel, add="+")
            widget.bind("<Button-4>", on_mousewheel_linux, add="+")
            widget.bind("<Button-5>", on_mousewheel_linux, add="+")
            for child in widget.winfo_children():
                bind_to_widget(child)

        canvas.bind("<MouseWheel>", on_mousewheel, add="+")
        canvas.bind("<Button-4>", on_mousewheel_linux, add="+")
        canvas.bind("<Button-5>", on_mousewheel_linux, add="+")
        bind_to_widget(scrollable_frame)

        self._scroll_bind_func = bind_to_widget
