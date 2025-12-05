# clipboard utilities for wayland and x11

import os
import subprocess
from typing import Optional


def is_wayland() -> bool:
    if os.environ.get('XDG_SESSION_TYPE') == 'wayland':
        return True
    if os.environ.get('WAYLAND_DISPLAY'):
        return True
    return False


def _get_x11_clipboard_xclip() -> Optional[str]:
    try:
        result = subprocess.run(
            ['xclip', '-selection', 'clipboard', '-o'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _get_x11_clipboard_xsel() -> Optional[str]:
    try:
        result = subprocess.run(
            ['xsel', '--clipboard', '--output'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _set_x11_clipboard_xclip(text: str) -> bool:
    try:
        process = subprocess.Popen(
            ['xclip', '-selection', 'clipboard'],
            stdin=subprocess.PIPE,
            text=True
        )
        process.communicate(input=text, timeout=2)
        return process.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return False


def _set_x11_clipboard_xsel(text: str) -> bool:
    try:
        process = subprocess.Popen(
            ['xsel', '--clipboard', '--input'],
            stdin=subprocess.PIPE,
            text=True
        )
        process.communicate(input=text, timeout=2)
        return process.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return False


def clipboard_get() -> Optional[str]:
    if is_wayland():
        try:
            result = subprocess.run(
                ['wl-paste', '--no-newline'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    # x11 - try xclip first then xsel
    content = _get_x11_clipboard_xclip()
    if content is not None:
        return content
    return _get_x11_clipboard_xsel()


def clipboard_set(text: str) -> bool:
    if is_wayland():
        try:
            process = subprocess.Popen(
                ['wl-copy'],
                stdin=subprocess.PIPE,
                text=True
            )
            process.communicate(input=text, timeout=2)
            return process.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return False

    # x11 - try xclip first then xsel
    if _set_x11_clipboard_xclip(text):
        return True
    return _set_x11_clipboard_xsel(text)
