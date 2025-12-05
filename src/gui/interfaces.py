"""protocol interfaces for frame-to-app communication

defines explicit interfaces using pythons protocol class for
dependency injection enabling better testability and decoupling between
frames and the main application
"""

from typing import Protocol, Any, Optional, Callable
from PIL import Image
from enum import Enum


class ConnectionState(Enum):
    """connection state enumeration"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class PrinterService(Protocol):
    """protocol for printer operations"""

    @property
    def is_printing(self) -> bool: ...

    def print_image(self, image: Image.Image) -> None: ...

    def cancel_print(self) -> None: ...


class StatusService(Protocol):
    """protocol for status bar and progress indicator operations"""

    def set_status(self, message: str) -> None: ...

    def show_progress(self, show: bool, cancel_callback: Optional[Callable] = None) -> None: ...

    def set_progress_value(self, percentage: int, message: str) -> None: ...


class SettingsService(Protocol):
    """protocol for application settings management
    """

    def get(self, key: str, default: Any = None) -> Any: ...

    def set(self, key: str, value: Any) -> None: ...

    def get_section(self, section: str) -> dict: ...

    def save(self) -> None: ...

    def save_immediate(self) -> None: ...


class ConnectionService(Protocol):
    """protocol for printer connection management"""

    @property
    def is_connected(self) -> bool: ...

    @property
    def state(self) -> ConnectionState: ...

    def connect(self, mac_address: str, device_name: str = "") -> None: ...

    def disconnect(self) -> None: ...


# adapter implementations for backward compatibility

class AppPrinterAdapter:
    """adapter to make the app instance conform to PrinterService protocol"""

    def __init__(self, app):
        self._app = app

    @property
    def is_printing(self) -> bool:
        return self._app.printing

    def print_image(self, image: Image.Image) -> None:
        self._app.print_image(image)

    def cancel_print(self) -> None:
        self._app.cancel_print()


class AppStatusAdapter:
    """adapter to make the app instance conform to StatusService protocol"""

    def __init__(self, app):
        self._app = app

    def set_status(self, message: str) -> None:
        self._app.set_status(message)

    def show_progress(self, show: bool, cancel_callback: Optional[Callable] = None) -> None:
        self._app.show_progress(show, cancel_callback)

    def set_progress_value(self, percentage: int, message: str) -> None:
        self._app.set_progress_value(percentage, message)


class AppSettingsAdapter:
    """adapter to make the app instance conform to SettingsService protocol"""

    def __init__(self, app):
        self._app = app

    def get(self, key: str, default: Any = None) -> Any:
        return self._app.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._app.settings.set(key, value)

    def get_section(self, section: str) -> dict:
        return self._app.settings.get_section(section)

    def save(self) -> None:
        self._app.settings.save()

    def save_immediate(self) -> None:
        self._app.settings.save_immediate()


class AppConnectionAdapter:
    """adapter to make the app instance conform to ConnectionService protocol"""

    def __init__(self, app):
        self._app = app

    @property
    def is_connected(self) -> bool:
        return self._app.printer is not None

    @property
    def state(self) -> ConnectionState:
        # map from apps connection state if it exists
        if hasattr(self._app, 'connection_state'):
            return self._app.connection_state
        # fallback to simple connected or disconnected
        return ConnectionState.CONNECTED if self.is_connected else ConnectionState.DISCONNECTED

    def connect(self, mac_address: str, device_name: str = "") -> None:
        self._app.connect_printer(mac_address, device_name)

    def disconnect(self) -> None:
        self._app.disconnect_printer()


def create_services_from_app(app) -> tuple[PrinterService, StatusService, SettingsService, ConnectionService]:
    """create service adapters from an app instance
    creates all service adapters from a main app instance
    for easy injection into frames while maintaining backward compatibility
    """
    return (
        AppPrinterAdapter(app),
        AppStatusAdapter(app),
        AppSettingsAdapter(app),
        AppConnectionAdapter(app)
    )
