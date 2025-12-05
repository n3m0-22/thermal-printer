import socket
import subprocess
import re
import time
import logging
from typing import Optional, List, Callable
from dataclasses import dataclass
from enum import Enum

from .protocol import PrinterProtocol
from ..config.defaults import (
    RECONNECT_MAX_ATTEMPTS,
    RECONNECT_BACKOFF_BASE,
    RECONNECT_BACKOFF_CAP_SECONDS,
    BLUETOOTH_COMMAND_TIMEOUT,
    BLUETOOTH_SCAN_POLL_INTERVAL,
    BLUETOOTH_PAIRING_RETRY_DELAY,
    BLUETOOTH_SCAN_STOP_TIMEOUT,
)
from .exceptions import (
    ConnectionError,
    DisconnectionError,
    NotConnectedError,
    AlreadyConnectedError,
    PrintError,
    StatusError,
    ScanError,
)

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class BluetoothDevice:
    mac_address: str
    name: str
    is_ctp_printer: bool = False

    @classmethod
    def from_scan_line(cls, mac: str, name: str) -> "BluetoothDevice":
        is_printer = name.lower().startswith("coreprint")
        return cls(mac_address=mac, name=name, is_ctp_printer=is_printer)


class PrinterConnection:
    RFCOMM_CHANNEL = 1
    SPP_UUID = "00001101-0000-1000-8000-00805f9b34fb"

    def __init__(self, auto_reconnect: bool = False, max_reconnect_attempts: int = RECONNECT_MAX_ATTEMPTS) -> None:
        self._socket: Optional[socket.socket] = None
        self._state: ConnectionState = ConnectionState.DISCONNECTED
        self._mac_address: Optional[str] = None
        self._device_name: Optional[str] = None
        self._state_callbacks: List[Callable[[ConnectionState], None]] = []
        self._auto_reconnect: bool = auto_reconnect
        self._max_reconnect_attempts: int = max_reconnect_attempts
        self._reconnect_attempts: int = 0
        self._last_successful_connection: Optional[float] = None
        self._discovered_channel: Optional[int] = None

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED and self._socket is not None

    @property
    def mac_address(self) -> Optional[str]:
        return self._mac_address

    @property
    def device_name(self) -> Optional[str]:
        return self._device_name

    @property
    def auto_reconnect(self) -> bool:
        return self._auto_reconnect

    @auto_reconnect.setter
    def auto_reconnect(self, value: bool) -> None:
        self._auto_reconnect = value

    @property
    def reconnect_attempts(self) -> int:
        return self._reconnect_attempts

    def add_state_callback(self, callback: Callable[[ConnectionState], None]) -> None:
        self._state_callbacks.append(callback)

    def remove_state_callback(self, callback: Callable[[ConnectionState], None]) -> None:
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)

    def _set_state(self, state: ConnectionState) -> None:
        self._state = state
        for callback in self._state_callbacks:
            try:
                callback(state)
            except Exception as e:
                logger.exception(f"Error in state callback: {e}")

    @staticmethod
    def discover_rfcomm_channel(mac_address: str) -> Optional[int]:
        # try sdptool first - most reliable for getting rfcomm channel
        try:
            result = subprocess.run(
                ["sdptool", "browse", mac_address],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                lines = result.stdout.split('\n')
                in_spp_service = False
                in_protocol_descriptor = False

                for i, line in enumerate(lines):
                    if 'Serial Port' in line or '0x1101' in line:
                        in_spp_service = True
                        continue

                    if line.startswith('Service Name:') or line.startswith('Service RecHandle:'):
                        if not in_protocol_descriptor:
                            in_spp_service = False

                    if in_spp_service and 'Protocol Descriptor List' in line:
                        in_protocol_descriptor = True
                        continue

                    if in_protocol_descriptor and 'Channel:' in line:
                        match = re.search(r'Channel:\s*(\d+)', line)
                        if match:
                            channel = int(match.group(1))
                            return channel

                    if in_protocol_descriptor and line.strip() and not line.startswith(' '):
                        in_protocol_descriptor = False

        except FileNotFoundError:
            pass
        except subprocess.TimeoutExpired:
            pass
        except (subprocess.SubprocessError, OSError, ValueError) as e:
            logger.debug(f"sdptool error: {e}")

        # try bluetoothctl as fallback - less reliable but more common
        try:
            result = subprocess.run(
                ["bluetoothctl", "info", mac_address],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # bluetoothctl doesnt show channel numbers directly
                if PrinterConnection.SPP_UUID in result.stdout or '00001101' in result.stdout:
                    pass

        except FileNotFoundError:
            pass
        except subprocess.TimeoutExpired:
            pass
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug(f"bluetoothctl info error: {e}")

        return None

    def connect(self, mac_address: str, device_name: Optional[str] = None,
                 discover_channel: bool = True) -> bool:
        if self.is_connected:
            raise AlreadyConnectedError("Already connected to a printer")

        self._set_state(ConnectionState.CONNECTING)
        self._mac_address = mac_address
        self._device_name = device_name

        # some printers use non-standard channels - try sdp discovery first
        channel = self.RFCOMM_CHANNEL
        if discover_channel:
            discovered = self.discover_rfcomm_channel(mac_address)
            if discovered is not None:
                channel = discovered
                self._discovered_channel = discovered

        try:
            self._socket = socket.socket(
                socket.AF_BLUETOOTH,
                socket.SOCK_STREAM,
                socket.BTPROTO_RFCOMM
            )
            self._socket.connect((mac_address, channel))
            self.get_status()
            self._set_state(ConnectionState.CONNECTED)
            self._reconnect_attempts = 0
            self._last_successful_connection = time.time()
            return True

        except socket.error as e:
            # sdp discovery might give wrong channel - fallback to default
            if discover_channel and channel != self.RFCOMM_CHANNEL:
                self._cleanup_socket()
                try:
                    self._socket = socket.socket(
                        socket.AF_BLUETOOTH,
                        socket.SOCK_STREAM,
                        socket.BTPROTO_RFCOMM
                    )
                    self._socket.connect((mac_address, self.RFCOMM_CHANNEL))
                    self.get_status()
                    self._set_state(ConnectionState.CONNECTED)
                    self._reconnect_attempts = 0
                    self._last_successful_connection = time.time()
                    self._discovered_channel = None
                    return True
                except socket.error as fallback_error:
                    self._cleanup_socket()
                    self._set_state(ConnectionState.ERROR)
                    raise ConnectionError(
                        f"Failed to connect to {mac_address} on both discovered "
                        f"channel {channel} and default channel {self.RFCOMM_CHANNEL}: {fallback_error}"
                    )
                except Exception as fallback_error:
                    self._cleanup_socket()
                    self._set_state(ConnectionState.ERROR)
                    raise ConnectionError(f"Unexpected error during fallback connection: {fallback_error}")

            self._cleanup_socket()
            self._set_state(ConnectionState.ERROR)
            raise ConnectionError(f"Failed to connect to {mac_address}: {e}")

        except Exception as e:
            self._cleanup_socket()
            self._set_state(ConnectionState.ERROR)
            raise ConnectionError(f"Unexpected error connecting: {e}")

    def disconnect(self) -> None:
        if not self.is_connected:
            raise NotConnectedError("Not connected to any printer")

        try:
            if self._socket:
                try:
                    # shutdown before close for clean disconnect
                    self._socket.shutdown(socket.SHUT_RDWR)
                except (OSError, socket.error):
                    pass

                try:
                    self._socket.close()
                except (OSError, socket.error) as e:
                    logger.warning(f"Error closing socket during disconnect: {e}")
        except Exception as e:
            raise DisconnectionError(f"Error during disconnection: {e}")
        finally:
            self._socket = None
            self._set_state(ConnectionState.DISCONNECTED)

    def _cleanup_socket(self) -> None:
        if self._socket:
            try:
                try:
                    self._socket.shutdown(socket.SHUT_RDWR)
                except (OSError, socket.error) as e:
                    logger.debug(f"Socket shutdown failed (expected if already closed): {e}")

                self._socket.close()
            except (OSError, socket.error) as e:
                logger.warning(f"Error closing socket: {e}")
            except Exception as e:
                logger.error(f"Unexpected error during socket cleanup: {e}")
            finally:
                self._socket = None

    def reconnect(self) -> bool:
        if not self._mac_address:
            raise ConnectionError("No previous connection to reconnect to")

        if self._reconnect_attempts >= self._max_reconnect_attempts:
            self._set_state(ConnectionState.ERROR)
            return False

        # exponential backoff to avoid hammering bluetooth stack
        delay = min(RECONNECT_BACKOFF_BASE ** self._reconnect_attempts, RECONNECT_BACKOFF_CAP_SECONDS)
        if self._reconnect_attempts > 0:
            time.sleep(delay)

        self._reconnect_attempts += 1

        channel = self._discovered_channel if self._discovered_channel is not None else self.RFCOMM_CHANNEL

        try:
            self._cleanup_socket()

            self._set_state(ConnectionState.CONNECTING)
            self._socket = socket.socket(
                socket.AF_BLUETOOTH,
                socket.SOCK_STREAM,
                socket.BTPROTO_RFCOMM
            )
            self._socket.connect((self._mac_address, channel))
            self.get_status()
            self._set_state(ConnectionState.CONNECTED)
            self._reconnect_attempts = 0
            self._last_successful_connection = time.time()
            return True

        except (OSError, socket.error) as e:
            logger.debug(f"Reconnection attempt {self._reconnect_attempts} failed: {e}")
            self._cleanup_socket()
            return False

        except Exception as e:
            logger.warning(f"Unexpected error during reconnection: {e}")
            self._cleanup_socket()
            return False

    def check_connection_quality(self) -> bool:
        if not self.is_connected:
            return False

        try:
            self.get_status()
            self._last_successful_connection = time.time()
            return True
        except (StatusError, NotConnectedError):
            return False

    def get_status(self) -> bytes:
        if not self._socket:
            raise NotConnectedError("Not connected to printer")

        try:
            self._socket.send(PrinterProtocol.CMD_STATUS_REQUEST)
            return self._socket.recv(PrinterProtocol.STATUS_RESPONSE_LENGTH)
        except socket.error as e:
            raise StatusError(f"Failed to get printer status: {e}")

    def send_raw(self, data: bytes, reconnect_on_failure: bool = False) -> None:
        if not self._socket:
            raise NotConnectedError("Not connected to printer")

        try:
            self._socket.send(data)
            self._last_successful_connection = time.time()
        except socket.error as e:
            should_reconnect = reconnect_on_failure or self._auto_reconnect

            if should_reconnect and self._mac_address:
                self._set_state(ConnectionState.ERROR)

                if self.reconnect():
                    try:
                        self._socket.send(data)
                        self._last_successful_connection = time.time()
                        return
                    except socket.error as retry_error:
                        raise PrintError(f"Failed to send data after reconnection: {retry_error}")
                else:
                    raise PrintError(f"Failed to send data and reconnection failed: {e}")
            else:
                raise PrintError(f"Failed to send data: {e}")

    def initialize(self) -> None:
        self.send_raw(PrinterProtocol.CMD_INITIALIZE)

    def start_print(self) -> None:
        self.send_raw(PrinterProtocol.CMD_START_PRINT)

    def end_print(self) -> None:
        self.send_raw(PrinterProtocol.CMD_END_PRINT)

    def send_image(self, image_data: bytes) -> None:
        self.send_raw(image_data)

    def __enter__(self) -> "PrinterConnection":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self.is_connected:
            try:
                self.disconnect()
            except Exception as e:
                logger.warning(f"Error during context manager disconnect: {e}")
                self._cleanup_socket()
        return False

    @staticmethod
    def scan_for_printers(timeout: int = 10) -> List[BluetoothDevice]:
        import time
        import select

        devices: List[BluetoothDevice] = []
        seen_macs: set = set()

        def parse_device_line(line: str) -> None:
            patterns = [
                r'Device\s+([0-9A-Fa-f:]{17})\s+(.+)',
                r'\[NEW\]\s+Device\s+([0-9A-Fa-f:]{17})\s+(.+)',
                r'\[CHG\]\s+Device\s+([0-9A-Fa-f:]{17})\s+Name:\s+(.+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    mac = match.group(1)
                    name = match.group(2).strip()
                    name = re.sub(r'\s+\[.*\]$', '', name)
                    if mac not in seen_macs and name and not name.startswith('Name:'):
                        seen_macs.add(mac)
                        device = BluetoothDevice.from_scan_line(mac, name)
                        devices.append(device)
                    break

        try:
            # get already paired devices first
            result = subprocess.run(
                ["bluetoothctl", "devices"],
                capture_output=True,
                text=True,
                timeout=BLUETOOTH_COMMAND_TIMEOUT
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    parse_device_line(line)

            # active scan for nearby devices
            try:
                scan_proc = subprocess.Popen(
                    ["bluetoothctl", "--timeout", str(timeout), "scan", "on"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                start_time = time.time()
                while time.time() - start_time < timeout:
                    if scan_proc.stdout:
                        try:
                            ready, _, _ = select.select([scan_proc.stdout], [], [], BLUETOOTH_SCAN_POLL_INTERVAL)
                            if ready:
                                line = scan_proc.stdout.readline()
                                if line:
                                    parse_device_line(line)
                        except (OSError, ValueError) as e:
                            logger.debug(f"Scan select error: {e}")
                            time.sleep(BLUETOOTH_SCAN_POLL_INTERVAL)
                    else:
                        time.sleep(BLUETOOTH_SCAN_POLL_INTERVAL)

                    if scan_proc.poll() is not None:
                        break

                # stop scan process if still running
                if scan_proc.poll() is None:
                    scan_proc.terminate()
                    try:
                        scan_proc.wait(timeout=BLUETOOTH_SCAN_STOP_TIMEOUT)
                    except subprocess.TimeoutExpired:
                        scan_proc.kill()

            except (subprocess.SubprocessError, OSError) as e:
                logger.debug(f"Scan process error: {e}")

            # grab final device list after scan completes
            result = subprocess.run(
                ["bluetoothctl", "devices"],
                capture_output=True,
                text=True,
                timeout=BLUETOOTH_COMMAND_TIMEOUT
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    parse_device_line(line)

        except FileNotFoundError:
            raise ScanError("bluetoothctl not found. Is bluez installed?")
        except subprocess.TimeoutExpired:
            raise ScanError("Bluetooth scan timed out")
        except Exception as e:
            raise ScanError(f"Bluetooth scan failed: {e}")

        # put ctp printers first in results
        devices.sort(key=lambda d: (not d.is_ctp_printer, d.name))
        return devices

    @staticmethod
    def validate_mac_address(mac: str) -> bool:
        pattern = r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$'
        return bool(re.match(pattern, mac))
