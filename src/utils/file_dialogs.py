# native file dialog utilities using xdg-desktop-portal, zenity, kdialog or tkinter fallback

import subprocess
import shutil
import os
import tempfile
import json
from typing import Optional, List, Tuple
from pathlib import Path


def _has_portal() -> bool:
    try:
        if not shutil.which("dbus-send"):
            return False

        # try to ping the filechooser portal to verify its running
        result = subprocess.run(
            [
                "dbus-send",
                "--session",
                "--print-reply",
                "--dest=org.freedesktop.portal.Desktop",
                "/org/freedesktop/portal/desktop",
                "org.freedesktop.DBus.Introspectable.Introspect"
            ],
            capture_output=True,
            timeout=2
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        return False


def _has_python_dbus() -> bool:
    try:
        import dbus
        return True
    except ImportError:
        return False


def _has_zenity() -> bool:
    return shutil.which("zenity") is not None


def _has_kdialog() -> bool:
    return shutil.which("kdialog") is not None


def _build_zenity_filter(filetypes: List[Tuple[str, str]]) -> List[str]:
    filters = []
    for name, pattern in filetypes:
        patterns = pattern.replace(";", " ")
        filters.extend(["--file-filter", f"{name} | {patterns}"])
    return filters


def _build_kdialog_filter(filetypes: List[Tuple[str, str]]) -> str:
    parts = []
    for name, pattern in filetypes:
        patterns = pattern.replace(";", " ")
        parts.append(f"{name} ({patterns})")
    return "|".join(parts)


class PortalFileDialog:
    @staticmethod
    def _build_portal_filters(filetypes: List[Tuple[str, str]]) -> List[Tuple[str, List[Tuple[int, str]]]]:
        filters = []
        for name, pattern in filetypes:
            patterns = []
            for p in pattern.split(";"):
                p = p.strip()
                if p and p != "*":
                    # portal uses glob patterns type 0
                    patterns.append((0, p))
                elif p == "*":
                    patterns.append((0, "*"))

            if patterns:
                filters.append((name, patterns))

        return filters

    @staticmethod
    def _open_file_dbus(title: str, filters: list, directory: Optional[str] = None) -> Optional[str]:
        try:
            import dbus
            from dbus.mainloop.glib import DBusGMainLoop
            from gi.repository import GLib

            DBusGMainLoop(set_as_default=True)

            bus = dbus.SessionBus()
            portal = bus.get_object(
                "org.freedesktop.portal.Desktop",
                "/org/freedesktop/portal/desktop"
            )
            file_chooser = dbus.Interface(
                portal,
                "org.freedesktop.portal.FileChooser"
            )

            handle_token = f"print_app_{os.getpid()}"
            options = {
                "handle_token": handle_token,
                "modal": True,
                "multiple": False,
            }

            if filters:
                options["filters"] = dbus.Array(
                    [(name, pats) for name, pats in filters],
                    signature="(sa(us))"
                )

            if directory:
                options["current_folder"] = dbus.ByteArray(directory.encode('utf-8'))

            result_uri = {"value": None, "done": False}

            def response_handler(response, results):
                result_uri["done"] = True
                if response == 0 and "uris" in results:
                    uris = results["uris"]
                    if uris and len(uris) > 0:
                        # convert file uri to path
                        uri = str(uris[0])
                        if uri.startswith("file://"):
                            result_uri["value"] = uri[7:]

                loop.quit()
            bus.add_signal_receiver(
                response_handler,
                signal_name="Response",
                dbus_interface="org.freedesktop.portal.Request",
                path_keyword="path"
            )

            request_path = file_chooser.OpenFile(
                "",
                title,
                options
            )

            # run event loop with 30s timeout
            loop = GLib.MainLoop()
            GLib.timeout_add(30000, loop.quit)
            loop.run()

            return result_uri.get("value")

        except Exception as e:
            return None

    @staticmethod
    def _save_file_dbus(title: str, filters: list, current_name: Optional[str] = None,
                        directory: Optional[str] = None) -> Optional[str]:
        try:
            import dbus
            from dbus.mainloop.glib import DBusGMainLoop
            from gi.repository import GLib

            DBusGMainLoop(set_as_default=True)

            bus = dbus.SessionBus()
            portal = bus.get_object(
                "org.freedesktop.portal.Desktop",
                "/org/freedesktop/portal/desktop"
            )
            file_chooser = dbus.Interface(
                portal,
                "org.freedesktop.portal.FileChooser"
            )

            handle_token = f"print_app_{os.getpid()}"

            options = {
                "handle_token": handle_token,
                "modal": True,
            }

            if filters:
                options["filters"] = dbus.Array(
                    [(name, pats) for name, pats in filters],
                    signature="(sa(us))"
                )

            if current_name:
                options["current_name"] = current_name

            if directory:
                options["current_folder"] = dbus.ByteArray(directory.encode('utf-8'))

            result_uri = {"value": None, "done": False}

            def response_handler(response, results):
                result_uri["done"] = True
                if response == 0 and "uris" in results:
                    uris = results["uris"]
                    if uris and len(uris) > 0:
                        uri = str(uris[0])
                        if uri.startswith("file://"):
                            result_uri["value"] = uri[7:]
                loop.quit()

            bus.add_signal_receiver(
                response_handler,
                signal_name="Response",
                dbus_interface="org.freedesktop.portal.Request",
                path_keyword="path"
            )

            request_path = file_chooser.SaveFile(
                "",
                title,
                options
            )

            loop = GLib.MainLoop()
            GLib.timeout_add(30000, loop.quit)
            loop.run()

            return result_uri.get("value")

        except Exception as e:
            return None

    @classmethod
    def open_file(cls, title: str, filetypes: List[Tuple[str, str]],
                  initialdir: Optional[str] = None) -> Optional[str]:
        if not _has_portal():
            return None

        filters = cls._build_portal_filters(filetypes)

        # python dbus is more reliable than dbus-send method
        if _has_python_dbus():
            return cls._open_file_dbus(title, filters, initialdir)

        return None

    @classmethod
    def save_file(cls, title: str, filetypes: List[Tuple[str, str]],
                  defaultextension: str = "", initialdir: Optional[str] = None,
                  initialfile: Optional[str] = None) -> Optional[str]:
        if not _has_portal():
            return None

        filters = cls._build_portal_filters(filetypes)

        current_name = initialfile
        if current_name and defaultextension and not current_name.endswith(defaultextension):
            current_name += defaultextension

        if _has_python_dbus():
            result = cls._save_file_dbus(title, filters, current_name, initialdir)
            if result and defaultextension and not result.endswith(defaultextension):
                # zenity and kdialog dont always add extension automatically
                if "." not in Path(result).name:
                    result += defaultextension
            return result

        return None


def open_file_dialog(
    title: str = "Open File",
    filetypes: Optional[List[Tuple[str, str]]] = None,
    initialdir: Optional[str] = None
) -> Optional[str]:
    if filetypes is None:
        filetypes = [("All files", "*")]

    # xdg desktop portal works on both wayland and x11
    if _has_portal():
        result = PortalFileDialog.open_file(title, filetypes, initialdir)
        if result is not None:
            return result

    # zenity for gtk gnome environments
    if _has_zenity():
        cmd = ["zenity", "--file-selection", f"--title={title}"]
        cmd.extend(_build_zenity_filter(filetypes))
        if initialdir:
            cmd.extend(["--filename", f"{initialdir}/"])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, Exception):
            pass

    # kdialog for kde environments
    if _has_kdialog():
        cmd = ["kdialog", "--getopenfilename"]
        if initialdir:
            cmd.append(initialdir)
        else:
            cmd.append(".")
        cmd.append(_build_kdialog_filter(filetypes))
        cmd.extend(["--title", title])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, Exception):
            pass

    # fall back to tkinter
    from tkinter import filedialog
    return filedialog.askopenfilename(
        title=title,
        filetypes=filetypes,
        initialdir=initialdir
    ) or None


def save_file_dialog(
    title: str = "Save File",
    filetypes: Optional[List[Tuple[str, str]]] = None,
    defaultextension: str = "",
    initialdir: Optional[str] = None,
    initialfile: Optional[str] = None
) -> Optional[str]:
    if filetypes is None:
        filetypes = [("All files", "*")]

    if _has_portal():
        result = PortalFileDialog.save_file(title, filetypes, defaultextension, initialdir, initialfile)
        if result is not None:
            return result

    if _has_zenity():
        cmd = ["zenity", "--file-selection", "--save", "--confirm-overwrite", f"--title={title}"]
        cmd.extend(_build_zenity_filter(filetypes))
        if initialdir and initialfile:
            cmd.extend(["--filename", f"{initialdir}/{initialfile}"])
        elif initialdir:
            cmd.extend(["--filename", f"{initialdir}/"])
        elif initialfile:
            cmd.extend(["--filename", initialfile])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                filepath = result.stdout.strip()
                # zenity doesnt always add extension automatically
                if defaultextension and "." not in filepath.split("/")[-1]:
                    filepath += defaultextension
                return filepath
            return None
        except (subprocess.TimeoutExpired, Exception):
            pass

    if _has_kdialog():
        cmd = ["kdialog", "--getsavefilename"]
        if initialdir:
            cmd.append(initialdir)
        else:
            cmd.append(".")
        cmd.append(_build_kdialog_filter(filetypes))
        cmd.extend(["--title", title])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                filepath = result.stdout.strip()
                if defaultextension and "." not in filepath.split("/")[-1]:
                    filepath += defaultextension
                return filepath
            return None
        except (subprocess.TimeoutExpired, Exception):
            pass

    # fall back to tkinter
    from tkinter import filedialog
    return filedialog.asksaveasfilename(
        title=title,
        filetypes=filetypes,
        defaultextension=defaultextension,
        initialdir=initialdir,
        initialfile=initialfile
    ) or None
