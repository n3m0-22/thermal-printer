"""wayland compositor detection and workaround utilities

provides methods to detect the wayland compositor and get compositor specific
workarounds for dialog positioning and window management
"""

import os
from typing import Dict, Optional


def is_wayland() -> bool:
    # check wayland display environment variable
    if os.environ.get("WAYLAND_DISPLAY"):
        return True

    # check xdg session type
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type == "wayland":
        return True

    return False


def detect_compositor() -> str:
    """detects compositor name: gnome kwin sway wlroots unknown"""
    # if not running wayland return unknown
    if not is_wayland():
        return "unknown"

    # check xdg current desktop for desktop environment
    current_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

    # gnome mutter compositor
    if "gnome" in current_desktop:
        return "gnome"

    # kde kwin compositor
    if "kde" in current_desktop or "plasma" in current_desktop:
        return "kwin"

    # sway compositor
    if "sway" in current_desktop:
        return "sway"

    # check desktop session as fallback
    desktop_session = os.environ.get("DESKTOP_SESSION", "").lower()

    if "gnome" in desktop_session:
        return "gnome"

    if "kde" in desktop_session or "plasma" in desktop_session:
        return "kwin"

    if "sway" in desktop_session:
        return "sway"

    # check for wlroots based compositors
    if any(comp in current_desktop for comp in ["wayfire", "river", "hyprland"]):
        return "wlroots"

    if any(comp in desktop_session for comp in ["wayfire", "river", "hyprland"]):
        return "wlroots"

    # on wayland but cant identify compositor
    return "unknown"


def get_wayland_workarounds() -> Dict[str, any]:
    """compositor specific workarounds for window management and dialog positioning"""
    compositor = detect_compositor()

    # wayland compositors need delayed grab or modal dialogs fail to get focus
    workarounds = {
        "gnome": {
            "positioning": "delayed",
            "grab_delay_ms": 100,
        },
        "kwin": {
            "positioning": "immediate",
            "grab_delay_ms": 50,
        },
        "sway": {
            "positioning": "delayed",
            "grab_delay_ms": 150,
        },
        "wlroots": {
            "positioning": "delayed",
            "grab_delay_ms": 150,
        },
    }

    # return compositor specific workarounds or default
    return workarounds.get(compositor, {
        "positioning": "delayed",
        "grab_delay_ms": 100,
    })


def get_compositor_info() -> Dict[str, any]:
    return {
        "is_wayland": is_wayland(),
        "compositor": detect_compositor(),
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP", ""),
        "session_type": os.environ.get("XDG_SESSION_TYPE", ""),
        "wayland_display": os.environ.get("WAYLAND_DISPLAY", ""),
        "workarounds": get_wayland_workarounds(),
    }
