# status bar component for displaying application state

from typing import Optional, Callable
import subprocess
import customtkinter as ctk


def check_bluetooth_status() -> bool:
    try:
        result = subprocess.run(
            ["bluetoothctl", "show"],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.returncode == 0:
            return "Powered: yes" in result.stdout
    except Exception:
        pass
    return False


class StatusBar(ctk.CTkFrame):

    def __init__(self, master, **kwargs):
        super().__init__(master, height=40, **kwargs)

        self._progress_visible = False
        self._cancel_callback: Optional[Callable] = None
        self._bt_status = False

        self._setup_ui()
        self._update_bluetooth_status()
        self._schedule_bt_check()

    def _setup_ui(self) -> None:
        self.pack_propagate(False)

        # bluetooth indicator (left side)
        self.bt_indicator = ctk.CTkLabel(
            self, text="BT: --",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=60
        )
        self.bt_indicator.pack(side="left", padx=(12, 8), pady=8)

        # left double separator
        sep_l1 = ctk.CTkFrame(self, width=1, fg_color="gray50")
        sep_l1.pack(side="left", fill="y", pady=6)

        sep_l2 = ctk.CTkFrame(self, width=1, fg_color="gray50")
        sep_l2.pack(side="left", fill="y", padx=(3, 12), pady=6)

        # progress section (center-left, expands)
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(side="left", fill="x", expand=True, padx=5)

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame, width=250, height=16
        )
        self.progress_bar.set(0)
        self.progress_bar.pack_forget()

        self.progress_percent = ctk.CTkLabel(
            self.progress_frame, text="",
            font=ctk.CTkFont(size=12), width=50
        )
        self.progress_percent.pack_forget()

        # cancel button hidden by default
        self.cancel_button = ctk.CTkButton(
            self, text="Cancel", width=70, height=26,
            font=ctk.CTkFont(size=12),
            fg_color=("red", "#BB0000"),
            hover_color=("darkred", "#880000"),
            command=self._on_cancel_click
        )
        self.cancel_button.pack_forget()

        # status message (right side)
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(side="right", padx=(0, 12))

        # right double separator
        sep_r2 = ctk.CTkFrame(self, width=1, fg_color="gray50")
        sep_r2.pack(side="right", fill="y", pady=6)

        sep_r1 = ctk.CTkFrame(self, width=1, fg_color="gray50")
        sep_r1.pack(side="right", fill="y", padx=(12, 3), pady=6)

        self.status_label = ctk.CTkLabel(
            self.status_frame, text="Ready",
            font=ctk.CTkFont(size=13),
            anchor="e"
        )
        self.status_label.pack(side="right")

    def set_status(self, message: str) -> None:
        self.status_label.configure(text=message)

    def show_progress(self, visible: bool, cancel_callback: Optional[Callable] = None) -> None:
        self._progress_visible = visible
        self._cancel_callback = cancel_callback

        if visible:
            self.progress_bar.pack(side="left", padx=(0, 8))
            self.progress_percent.pack(side="left")
            if cancel_callback:
                self.cancel_button.pack(side="left", padx=8)
            self.progress_bar.set(0)
        else:
            self.progress_bar.pack_forget()
            self.progress_percent.pack_forget()
            self.cancel_button.pack_forget()
            self._cancel_callback = None

    def set_progress_value(self, percent: int, message: str = "") -> None:
        self.progress_bar.set(percent / 100.0)
        self.progress_percent.configure(text=f"{percent}%")
        if message:
            self.status_label.configure(text=message)

    def _on_cancel_click(self) -> None:
        if self._cancel_callback:
            self._cancel_callback()

    def clear_status(self) -> None:
        self.status_label.configure(text="Ready")

    def _update_bluetooth_status(self) -> None:
        self._bt_status = check_bluetooth_status()
        if self._bt_status:
            self.bt_indicator.configure(text="BT: ON", text_color=("green", "#00CC00"))
        else:
            self.bt_indicator.configure(text="BT: OFF", text_color=("red", "#FF4444"))

    def _schedule_bt_check(self) -> None:
        self._update_bluetooth_status()
        self.after(5000, self._schedule_bt_check)
