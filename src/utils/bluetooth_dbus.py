"""bluetooth scanning implementation using python-dbus

dbus based implementation offers better control and async capabilities
compared to subprocess calls to bluetoothctl
"""

import logging
import time
from dataclasses import dataclass
from typing import List, Callable, Optional, Dict, Any
from threading import Thread, Event

from ..config.defaults import BLUETOOTH_COMMAND_TIMEOUT

# try to import dbus and fall back gracefully if not available
try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    try:
        from gi.repository import GLib
        HAS_GLIB = True
    except ImportError:
        HAS_GLIB = False
    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False
    HAS_GLIB = False

logger = logging.getLogger(__name__)


@dataclass
class BluetoothDevice:
    address: str
    name: str
    rssi: Optional[int] = None
    paired: bool = False
    connected: bool = False
    uuids: List[str] = None

    def __post_init__(self):
        if self.uuids is None:
            self.uuids = []


class BluetoothDBus:
    """dbus based bluetooth interface using bluez"""

    BLUEZ_SERVICE = "org.bluez"
    ADAPTER_INTERFACE = "org.bluez.Adapter1"
    DEVICE_INTERFACE = "org.bluez.Device1"
    OBJECT_MANAGER_INTERFACE = "org.freedesktop.DBus.ObjectManager"
    PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"

    def __init__(self):
        if not HAS_DBUS:
            raise RuntimeError("python-dbus not available")

        # initialize dbus main loop
        DBusGMainLoop(set_as_default=True)

        try:
            self.bus = dbus.SystemBus()
        except dbus.exceptions.DBusException as e:
            logger.error(f"Failed to connect to system D-Bus: {e}")
            raise RuntimeError(f"D-Bus connection failed: {e}")

        self.adapter_path = self._find_adapter()
        if not self.adapter_path:
            raise RuntimeError("No Bluetooth adapter found")

        self.adapter = dbus.Interface(
            self.bus.get_object(self.BLUEZ_SERVICE, self.adapter_path),
            self.ADAPTER_INTERFACE
        )
        self.adapter_props = dbus.Interface(
            self.bus.get_object(self.BLUEZ_SERVICE, self.adapter_path),
            self.PROPERTIES_INTERFACE
        )

        logger.info(f"Initialized Bluetooth adapter: {self.adapter_path}")

    def _find_adapter(self) -> Optional[str]:
        try:
            manager = dbus.Interface(
                self.bus.get_object(self.BLUEZ_SERVICE, "/"),
                self.OBJECT_MANAGER_INTERFACE
            )
            objects = manager.GetManagedObjects()

            for path, interfaces in objects.items():
                if self.ADAPTER_INTERFACE in interfaces:
                    return path

        except dbus.exceptions.DBusException as e:
            logger.error(f"Error finding adapter: {e}")

        return None

    def is_bluetooth_enabled(self) -> bool:
        try:
            powered = self.adapter_props.Get(self.ADAPTER_INTERFACE, "Powered")
            return bool(powered)
        except dbus.exceptions.DBusException as e:
            logger.error(f"Failed to get Bluetooth power state: {e}")
            return False

    def enable_bluetooth(self) -> bool:
        try:
            self.adapter_props.Set(
                self.ADAPTER_INTERFACE,
                "Powered",
                dbus.Boolean(True)
            )
            # wait briefly for adapter to power on
            time.sleep(0.5)
            return self.is_bluetooth_enabled()
        except dbus.exceptions.DBusException as e:
            logger.error(f"Failed to enable Bluetooth: {e}")
            return False

    def start_discovery(self) -> None:
        try:
            # ensure adapter is powered
            if not self.is_bluetooth_enabled():
                if not self.enable_bluetooth():
                    raise RuntimeError("Failed to power on Bluetooth adapter")

            self.adapter.StartDiscovery()
            logger.info("Bluetooth discovery started")
        except dbus.exceptions.DBusException as e:
            logger.error(f"Failed to start discovery: {e}")
            raise RuntimeError(f"Discovery start failed: {e}")

    def stop_discovery(self) -> None:
        try:
            self.adapter.StopDiscovery()
            logger.info("Bluetooth discovery stopped")
        except dbus.exceptions.DBusException as e:
            # discovery may already be stopped
            logger.debug(f"Error stopping discovery: {e}")

    def get_devices(self) -> List[BluetoothDevice]:
        devices = []

        try:
            manager = dbus.Interface(
                self.bus.get_object(self.BLUEZ_SERVICE, "/"),
                self.OBJECT_MANAGER_INTERFACE
            )
            objects = manager.GetManagedObjects()

            for path, interfaces in objects.items():
                if self.DEVICE_INTERFACE not in interfaces:
                    continue

                props = interfaces[self.DEVICE_INTERFACE]

                address = str(props.get("Address", ""))
                name = str(props.get("Name", props.get("Alias", "Unknown")))
                rssi = int(props.get("RSSI", 0)) if "RSSI" in props else None
                paired = bool(props.get("Paired", False))
                connected = bool(props.get("Connected", False))
                uuids = [str(uuid) for uuid in props.get("UUIDs", [])]

                device = BluetoothDevice(
                    address=address,
                    name=name,
                    rssi=rssi,
                    paired=paired,
                    connected=connected,
                    uuids=uuids
                )
                devices.append(device)

        except dbus.exceptions.DBusException as e:
            logger.error(f"Failed to get devices: {e}")

        return devices

    def async_scan(
        self,
        callback: Callable[[List[BluetoothDevice]], None],
        timeout: int = 10
    ) -> None:
        if not HAS_GLIB:
            # glib not available so use simple threaded scan instead
            self._threaded_scan(callback, timeout)
            return

        # use glib mainloop for proper dbus event handling
        self._glib_scan(callback, timeout)

    def _threaded_scan(
        self,
        callback: Callable[[List[BluetoothDevice]], None],
        timeout: int
    ) -> None:
        """simple threaded scan fallback when glib unavailable"""
        stop_event = Event()

        def scan_thread():
            try:
                self.start_discovery()

                # poll for devices during timeout
                elapsed = 0
                interval = 1

                while elapsed < timeout and not stop_event.is_set():
                    time.sleep(interval)
                    elapsed += interval

                    devices = self.get_devices()
                    callback(devices)

            finally:
                self.stop_discovery()

        thread = Thread(target=scan_thread, daemon=True)
        thread.start()

    def _glib_scan(
        self,
        callback: Callable[[List[BluetoothDevice]], None],
        timeout: int
    ) -> None:
        """glib mainloop based async scan with event handling"""
        mainloop = GLib.MainLoop()

        def update_callback():
            devices = self.get_devices()
            callback(devices)
            return True

        def timeout_callback():
            self.stop_discovery()
            mainloop.quit()
            return False

        def run_mainloop():
            try:
                self.start_discovery()

                # schedule periodic updates
                GLib.timeout_add_seconds(1, update_callback)

                # schedule timeout
                GLib.timeout_add_seconds(timeout, timeout_callback)

                mainloop.run()
            except Exception as e:
                logger.error(f"Mainloop error: {e}")
                mainloop.quit()

        thread = Thread(target=run_mainloop, daemon=True)
        thread.start()


# wrapper functions matching existing bluetooth py api


def scan_for_printers(timeout: int = 10) -> List[Dict[str, Any]]:
    """synchronous scan using dbus if available falls back to subprocess"""
    if not HAS_DBUS:
        logger.info("D-Bus not available, falling back to subprocess method")
        from . import bluetooth
        # this would call the subprocess version
        # for now return empty list as fallback will be in bluetooth py
        return []

    try:
        bt = BluetoothDBus()
        bt.start_discovery()

        # wait for scan to complete
        time.sleep(timeout)

        devices = bt.get_devices()
        bt.stop_discovery()

        # convert to dict format for compatibility
        return [
            {
                "address": device.address,
                "name": device.name,
                "rssi": device.rssi,
                "paired": device.paired
            }
            for device in devices
        ]

    except Exception as e:
        logger.error(f"D-Bus scan failed: {e}")
        return []


def async_scan_for_printers(
    callback: Callable[[List[Dict[str, Any]]], None],
    timeout: int = 10
) -> None:
    if not HAS_DBUS:
        logger.info("D-Bus not available, using fallback")
        # fallback will be handled in bluetooth py
        callback([])
        return

    try:
        bt = BluetoothDBus()

        def wrapper_callback(devices: List[BluetoothDevice]):
            device_dicts = [
                {
                    "address": device.address,
                    "name": device.name,
                    "rssi": device.rssi,
                    "paired": device.paired
                }
                for device in devices
            ]
            callback(device_dicts)

        bt.async_scan(wrapper_callback, timeout)

    except Exception as e:
        logger.error(f"Async D-Bus scan failed: {e}")
        callback([])
