# bluetooth connection frame for printer management

from typing import Optional, Callable, TYPE_CHECKING
import customtkinter as ctk

from ...core.printer import PrinterConnection, ConnectionState, BluetoothDevice
from ...config.keys import SettingsKeys
from ...config.settings import get_settings
from ...utils.validators import validate_mac_address, normalize_mac_address

if TYPE_CHECKING:
    from ...interfaces import SettingsService


class ConnectionFrame(ctk.CTkFrame):

    def __init__(
        self,
        master,
        printer: PrinterConnection,
        on_scan_request: Optional[Callable] = None,
        on_status_change: Optional[Callable[[str], None]] = None,
        on_bluetooth_check: Optional[Callable[[], bool]] = None,
        settings_service: Optional["SettingsService"] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)

        self.printer = printer
        self.on_scan_request = on_scan_request
        self.on_status_change = on_status_change
        self.on_bluetooth_check = on_bluetooth_check

        self._settings = settings_service if settings_service else get_settings()
        self._setup_ui()
        self._load_settings()

        self.printer.add_state_callback(self._on_connection_state_change)

    def _setup_ui(self) -> None:
        label_font = ctk.CTkFont(size=15, weight="bold")
        entry_font = ctk.CTkFont(size=14)
        btn_font = ctk.CTkFont(size=14)
        status_font = ctk.CTkFont(size=15, weight="bold")

        # single row with printer label mac entry buttons and status
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(
            row, text="MAC:",
            font=label_font
        ).pack(side="left", padx=(0, 10))

        self.mac_entry = ctk.CTkEntry(
            row, placeholder_text="XX:XX:XX:XX:XX:XX",
            width=180, height=36,
            font=entry_font
        )
        self.mac_entry.pack(side="left", padx=(0, 12))

        btn_width = 100
        btn_height = 36

        self.scan_button = ctk.CTkButton(
            row, text="Scan",
            width=btn_width, height=btn_height,
            font=btn_font,
            command=self._on_scan_click
        )
        self.scan_button.pack(side="left", padx=(0, 8))

        self.connect_button = ctk.CTkButton(
            row, text="Connect",
            width=btn_width, height=btn_height,
            font=btn_font,
            command=self._on_connect_click
        )
        self.connect_button.pack(side="left", padx=(0, 8))

        self.disconnect_button = ctk.CTkButton(
            row, text="Disconnect",
            width=btn_width, height=btn_height,
            font=btn_font,
            state="disabled",
            command=self._on_disconnect_click
        )
        self.disconnect_button.pack(side="left", padx=(0, 12))

        # device name label (next to disconnect button)
        self.printer_label = ctk.CTkLabel(
            row, text="Printer:",
            font=label_font,
            text_color=("gray50", "gray50")
        )
        self.printer_label.pack(side="left", padx=(0, 4))

        self.device_name_label = ctk.CTkLabel(
            row, text="--",
            font=entry_font,
            text_color=("gray50", "gray50")
        )
        self.device_name_label.pack(side="left", padx=(0, 15))

        self.status_label = ctk.CTkLabel(
            row, text="[ ] Disconnected",
            font=status_font,
            text_color=("gray50", "gray50")
        )
        self.status_label.pack(side="right", padx=(15, 0))

    def _load_settings(self) -> None:
        mac = self._settings.get(SettingsKeys.Printer.MAC_ADDRESS, "")
        if mac:
            self.mac_entry.insert(0, mac)

        device_name = self._settings.get(SettingsKeys.Printer.DEVICE_NAME, "")
        self._update_device_name(device_name)

    def _update_device_name(self, name: str) -> None:
        if name:
            self.device_name_label.configure(text=name)
        else:
            self.device_name_label.configure(text="--")

    def _save_settings(self, mac: str, device_name: str = "") -> None:
        self._settings.set(SettingsKeys.Printer.MAC_ADDRESS, mac)
        self._settings.set(SettingsKeys.Printer.DEVICE_NAME, device_name)
        self._settings.save()

    def _on_scan_click(self) -> None:
        if self.on_scan_request:
            self.on_scan_request()

    def _on_connect_click(self) -> None:
        if self.on_bluetooth_check and not self.on_bluetooth_check():
            return

        mac = self.mac_entry.get().strip()

        is_valid, error = validate_mac_address(mac)
        if not is_valid:
            self._show_error(error or "Invalid MAC address")
            return

        mac = normalize_mac_address(mac)
        self.mac_entry.delete(0, "end")
        self.mac_entry.insert(0, mac)

        self.connect_button.configure(state="disabled")
        self.scan_button.configure(state="disabled")
        self._set_status("Connecting...")

        try:
            device_name = self._settings.get(SettingsKeys.Printer.DEVICE_NAME, "")
            self.printer.connect(mac, device_name)
            self._save_settings(mac, device_name)
        except Exception as e:
            self._show_error(str(e))
            self.connect_button.configure(state="normal")
            self.scan_button.configure(state="normal")

    def _on_disconnect_click(self) -> None:
        self.disconnect_button.configure(state="disabled")
        self._set_status("Disconnecting...")

        try:
            self.printer.disconnect()
        except Exception as e:
            self._show_error(str(e))
        finally:
            self.disconnect_button.configure(state="normal")

    def _on_connection_state_change(self, state: ConnectionState) -> None:
        # connection state changes control ui button states and visual feedback
        # connected state disables connection controls and enables disconnect
        # disconnected and error states reset to allow new connection attempts
        if state == ConnectionState.CONNECTED:
            self.connect_button.configure(state="disabled")
            self.disconnect_button.configure(state="normal")
            self.scan_button.configure(state="disabled")
            self.mac_entry.configure(state="disabled")

            device_name = self.printer.device_name or ""
            self._update_device_name(device_name)
            self.device_name_label.configure(text_color=("green", "#00CC00"))
            self.status_label.configure(
                text="[*] Connected",
                text_color=("green", "#00CC00")
            )
            self._set_status("Connected to printer")

        elif state == ConnectionState.CONNECTING:
            self.status_label.configure(
                text="[~] Connecting...",
                text_color=("orange", "#FFAA00")
            )

        elif state == ConnectionState.DISCONNECTED:
            self.connect_button.configure(state="normal")
            self.disconnect_button.configure(state="disabled")
            self.scan_button.configure(state="normal")
            self.mac_entry.configure(state="normal")

            self.device_name_label.configure(text_color=("gray50", "gray50"))
            self.status_label.configure(
                text="[ ] Disconnected",
                text_color=("gray50", "gray50")
            )
            self._set_status("Disconnected")

        elif state == ConnectionState.ERROR:
            self.connect_button.configure(state="normal")
            self.disconnect_button.configure(state="disabled")
            self.scan_button.configure(state="normal")
            self.mac_entry.configure(state="normal")

            self.device_name_label.configure(text_color=("red", "#FF4444"))
            self.status_label.configure(
                text="[!] Error",
                text_color=("red", "#FF4444")
            )

    def _set_status(self, message: str) -> None:
        if self.on_status_change:
            self.on_status_change(message)

    def _show_error(self, message: str) -> None:
        self._set_status(f"Error: {message}")
        self.status_label.configure(
            text="[!] Error",
            text_color=("red", "#FF4444")
        )

    def set_device(self, device: BluetoothDevice) -> None:
        self.mac_entry.delete(0, "end")
        self.mac_entry.insert(0, device.mac_address)
        self._update_device_name(device.name)
        self._settings.set(SettingsKeys.Printer.DEVICE_NAME, device.name)

    def destroy(self) -> None:
        self.printer.remove_state_callback(self._on_connection_state_change)
        super().destroy()
