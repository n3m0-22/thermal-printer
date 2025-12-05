from typing import Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ..gui.interfaces import SettingsService

from .printer import PrinterConnection, ConnectionState
from ..config.settings import get_settings
from ..config.keys import SettingsKeys


class ConnectionController:
    def __init__(
        self,
        printer: Optional[PrinterConnection] = None,
        settings_service: Optional["SettingsService"] = None,
    ) -> None:
        self._printer = printer if printer is not None else PrinterConnection()
        self._settings = settings_service if settings_service is not None else get_settings()

    @property
    def is_connected(self) -> bool:
        return self._printer.is_connected

    @property
    def state(self) -> ConnectionState:
        return self._printer.state

    @property
    def mac_address(self) -> Optional[str]:
        return self._printer.mac_address

    @property
    def device_name(self) -> Optional[str]:
        return self._printer.device_name

    @property
    def printer(self) -> PrinterConnection:
        return self._printer

    def add_state_callback(self, callback: Callable[[ConnectionState], None]) -> None:
        self._printer.add_state_callback(callback)

    def remove_state_callback(self, callback: Callable[[ConnectionState], None]) -> None:
        self._printer.remove_state_callback(callback)

    def connect(self, mac_address: str, device_name: Optional[str] = None) -> bool:
        return self._printer.connect(mac_address, device_name)

    def disconnect(self) -> None:
        self._printer.disconnect()

    def auto_connect(self) -> bool:
        mac = self._settings.get(SettingsKeys.Printer.MAC_ADDRESS, "")
        name = self._settings.get(SettingsKeys.Printer.DEVICE_NAME, "")

        if not mac:
            return False

        try:
            self._printer.connect(mac, name)
            return True
        except Exception:
            return False
