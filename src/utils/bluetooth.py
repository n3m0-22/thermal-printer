"""bluetooth utilities for checking and enabling bluetooth"""

import subprocess
import shutil
import logging
from typing import List, Dict, Any, Callable

from ..config.defaults import BLUETOOTH_COMMAND_TIMEOUT, BLUETOOTH_PAIRING_RETRY_DELAY

# try to use dbus implementation if available
try:
    from .bluetooth_dbus import (
        BluetoothDBus,
        scan_for_printers as dbus_scan_for_printers,
        async_scan_for_printers as dbus_async_scan_for_printers,
        HAS_DBUS
    )
except ImportError:
    HAS_DBUS = False

logger = logging.getLogger(__name__)


def _subprocess_is_bluetooth_enabled() -> bool:
    """fallback implementation when dbus is not available"""
    # try bluetoothctl first
    if shutil.which("bluetoothctl"):
        try:
            result = subprocess.run(
                ["bluetoothctl", "show"],
                capture_output=True,
                text=True,
                timeout=BLUETOOTH_COMMAND_TIMEOUT
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "Powered:" in line:
                        return "yes" in line.lower()
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass

    # fallback to rfkill if bluetoothctl unavailable
    if shutil.which("rfkill"):
        try:
            result = subprocess.run(
                ["rfkill", "list", "bluetooth"],
                capture_output=True,
                text=True,
                timeout=BLUETOOTH_COMMAND_TIMEOUT
            )
            if result.returncode == 0:
                output = result.stdout.lower()
                if "soft blocked: yes" in output or "hard blocked: yes" in output:
                    return False
                if "bluetooth" in output:
                    return True
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass

    # if we cant determine assume its on to avoid blocking user
    return True


def _subprocess_enable_bluetooth() -> bool:
    """fallback implementation when dbus is not available"""
    import time

    # rfkill unblock handles soft block
    if shutil.which("rfkill"):
        try:
            subprocess.run(
                ["rfkill", "unblock", "bluetooth"],
                capture_output=True,
                timeout=BLUETOOTH_COMMAND_TIMEOUT
            )
            # rfkill needs time to complete unblock before power on
            time.sleep(BLUETOOTH_PAIRING_RETRY_DELAY)
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass

    # then power on via bluetoothctl
    if shutil.which("bluetoothctl"):
        try:
            result = subprocess.run(
                ["bluetoothctl", "power", "on"],
                capture_output=True,
                text=True,
                timeout=BLUETOOTH_COMMAND_TIMEOUT
            )
            output = result.stdout.lower() + result.stderr.lower()
            if "succeeded" in output or "already on" in output:
                return True
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass

    return False


# public api functions with dbus fallback


def is_bluetooth_enabled() -> bool:
    """uses dbus if available falls back to subprocess methods"""
    if HAS_DBUS:
        try:
            bt = BluetoothDBus()
            return bt.is_bluetooth_enabled()
        except Exception as e:
            logger.warning(f"D-Bus method failed, falling back to subprocess: {e}")

    return _subprocess_is_bluetooth_enabled()


def enable_bluetooth() -> bool:
    """uses dbus if available falls back to subprocess methods"""
    if HAS_DBUS:
        try:
            bt = BluetoothDBus()
            return bt.enable_bluetooth()
        except Exception as e:
            logger.warning(f"D-Bus method failed, falling back to subprocess: {e}")

    return _subprocess_enable_bluetooth()


def scan_for_printers(timeout: int = 10) -> List[Dict[str, Any]]:
    """uses dbus async scanning if available for better control falls back to subprocess bluetoothctl"""
    if HAS_DBUS:
        try:
            logger.info("Using D-Bus for Bluetooth scanning")
            return dbus_scan_for_printers(timeout)
        except Exception as e:
            logger.warning(f"D-Bus scan failed, falling back to subprocess: {e}")

    # fallback to subprocess implementation
    logger.info("Using subprocess for Bluetooth scanning")
    return _subprocess_scan_for_printers(timeout)


def async_scan_for_printers(
    callback: Callable[[List[Dict[str, Any]]], None],
    timeout: int = 10
) -> None:
    """uses dbus with glib mainloop if available for true async operation falls back to threaded subprocess"""
    if HAS_DBUS:
        try:
            logger.info("Using D-Bus for async Bluetooth scanning")
            dbus_async_scan_for_printers(callback, timeout)
            return
        except Exception as e:
            logger.warning(f"D-Bus async scan failed, falling back: {e}")

    # fallback to subprocess implementation
    logger.info("Using subprocess for async Bluetooth scanning")
    _subprocess_async_scan_for_printers(callback, timeout)


def _subprocess_scan_for_printers(timeout: int = 10) -> List[Dict[str, Any]]:
    """subprocess implementation fallback when dbus unavailable"""
    import time

    devices = []

    if not shutil.which("bluetoothctl"):
        logger.warning("bluetoothctl not found")
        return devices

    try:
        # start scan
        subprocess.run(
            ["bluetoothctl", "scan", "on"],
            capture_output=True,
            timeout=BLUETOOTH_COMMAND_TIMEOUT
        )

        # wait for scan
        time.sleep(timeout)

        # get devices
        result = subprocess.run(
            ["bluetoothctl", "devices"],
            capture_output=True,
            text=True,
            timeout=BLUETOOTH_COMMAND_TIMEOUT
        )

        # stop scan
        subprocess.run(
            ["bluetoothctl", "scan", "off"],
            capture_output=True,
            timeout=BLUETOOTH_COMMAND_TIMEOUT
        )

        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if line.startswith("Device"):
                    parts = line.split(maxsplit=2)
                    if len(parts) >= 3:
                        devices.append({
                            "address": parts[1],
                            "name": parts[2],
                            "rssi": None,
                            "paired": False
                        })

    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        logger.error(f"Subprocess scan failed: {e}")

    return devices


def _subprocess_async_scan_for_printers(
    callback: Callable[[List[Dict[str, Any]]], None],
    timeout: int = 10
) -> None:
    """subprocess implementation fallback when dbus unavailable"""
    from threading import Thread
    import time

    def scan_thread():
        if not shutil.which("bluetoothctl"):
            callback([])
            return

        try:
            # start scan
            subprocess.run(
                ["bluetoothctl", "scan", "on"],
                capture_output=True,
                timeout=BLUETOOTH_COMMAND_TIMEOUT
            )

            # poll for devices during timeout
            elapsed = 0
            interval = 1

            while elapsed < timeout:
                time.sleep(interval)
                elapsed += interval

                # get current devices
                result = subprocess.run(
                    ["bluetoothctl", "devices"],
                    capture_output=True,
                    text=True,
                    timeout=BLUETOOTH_COMMAND_TIMEOUT
                )

                devices = []
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if line.startswith("Device"):
                            parts = line.split(maxsplit=2)
                            if len(parts) >= 3:
                                devices.append({
                                    "address": parts[1],
                                    "name": parts[2],
                                    "rssi": None,
                                    "paired": False
                                })

                callback(devices)

        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            logger.error(f"Async subprocess scan failed: {e}")
            callback([])
        finally:
            # stop scan
            try:
                subprocess.run(
                    ["bluetoothctl", "scan", "off"],
                    capture_output=True,
                    timeout=BLUETOOTH_COMMAND_TIMEOUT
                )
            except Exception:
                pass

    thread = Thread(target=scan_thread, daemon=True)
    thread.start()
