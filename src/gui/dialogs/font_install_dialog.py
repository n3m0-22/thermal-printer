# font installation dialog with OS-specific instructions

import customtkinter as ctk
from typing import Optional

from .centered_dialog import CenteredDialog
from ...utils.clipboard import clipboard_set


# installation commands for Linux package managers
INSTALL_COMMANDS = [
    {
        "title": "Debian / Ubuntu / Mint (apt)",
        "command": "sudo apt install fonts-dejavu",
    },
    {
        "title": "Fedora / RHEL (dnf)",
        "command": "sudo dnf install dejavu-sans-fonts",
    },
    {
        "title": "Arch Linux (pacman)",
        "command": "sudo pacman -S ttf-dejavu",
    },
]

# wsl runs linux distros so users need the linux package manager
WSL_NOTE = "Windows users: This app runs through WSL. Use the install command for your WSL Linux distribution."

FONT_NAME = "DejaVuSans"


class FontInstallDialog(CenteredDialog):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            title="Font Required",
            width=520,
            height=580,
            **kwargs
        )

    def _build_content(self) -> None:
        label_font = ctk.CTkFont(size=14)
        title_font = ctk.CTkFont(size=16, weight="bold")
        code_font = ctk.CTkFont(size=13, family="monospace")

        # main message
        ctk.CTkLabel(
            self.content_frame,
            text="'DejaVu Sans' font is required",
            font=title_font
        ).pack(pady=(0, 10))

        ctk.CTkLabel(
            self.content_frame,
            text="This font provides the best support for Unicode characters\n"
                 "including math symbols, Greek letters, and special characters.",
            font=label_font,
            justify="center"
        ).pack(pady=(0, 15))

        # installation instructions for each distro
        for info in INSTALL_COMMANDS:
            self._create_distro_section(info, label_font, code_font)

        # wsl note
        wsl_frame = ctk.CTkFrame(self.content_frame, fg_color=("gray88", "gray22"))
        wsl_frame.pack(fill="x", pady=(15, 10), padx=5)

        ctk.CTkLabel(
            wsl_frame,
            text=WSL_NOTE,
            font=ctk.CTkFont(size=14),
            text_color=("gray20", "gray85"),
            wraplength=450
        ).pack(pady=12, padx=15)

        # restart note
        note_frame = ctk.CTkFrame(self.content_frame, fg_color=("gray90", "gray20"))
        note_frame.pack(fill="x", pady=(10, 10))

        ctk.CTkLabel(
            note_frame,
            text="Please restart the application after installing the font.",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("gray20", "gray80")
        ).pack(pady=10, padx=10)

        # close button
        close_btn = ctk.CTkButton(
            self.content_frame,
            text="Close",
            width=100,
            height=36,
            font=ctk.CTkFont(size=14),
            command=self._on_close
        )
        close_btn.pack(pady=(5, 0))

    def _create_distro_section(
        self,
        info: dict,
        label_font: ctk.CTkFont,
        code_font: ctk.CTkFont
    ) -> None:
        section = ctk.CTkFrame(
            self.content_frame,
            fg_color="transparent",
            corner_radius=8
        )
        section.pack(fill="x", pady=3, padx=5)

        # distro title
        ctk.CTkLabel(
            section,
            text=info["title"],
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        ).pack(fill="x", padx=10, pady=(5, 2))

        # command with copy button
        cmd_frame = ctk.CTkFrame(section, fg_color="transparent")
        cmd_frame.pack(fill="x", padx=10, pady=(0, 5))

        cmd_entry = ctk.CTkEntry(
            cmd_frame,
            font=code_font,
            height=32,
            state="normal"
        )
        cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        cmd_entry.insert(0, info["command"])
        cmd_entry.configure(state="readonly")

        copy_btn = ctk.CTkButton(
            cmd_frame,
            text="Copy",
            width=60,
            height=32,
            font=ctk.CTkFont(size=12),
            command=lambda cmd=info["command"], btn=None: self._copy_command(cmd, btn)
        )
        copy_btn.pack(side="right")
        # store reference for feedback
        copy_btn._cmd = info["command"]
        copy_btn.configure(command=lambda b=copy_btn: self._copy_command(b._cmd, b))

    def _copy_command(self, command: str, button: Optional[ctk.CTkButton]) -> None:
        success = clipboard_set(command)
        if not success:
            # fallback to tkinter clipboard
            try:
                self.clipboard_clear()
                self.clipboard_append(command)
                success = True
            except Exception:
                pass

        if button and success:
            original_text = button.cget("text")
            button.configure(text="Copied!")
            self.after(1500, lambda: button.configure(text=original_text))


class FontSwitchNotification(CenteredDialog):
    # shown when unicode characters force dejavu font switch
    def __init__(
        self,
        master,
        original_font: str,
        new_font: str,
        on_disable_popup: Optional[callable] = None,
        **kwargs
    ):
        self.original_font = original_font
        self.new_font = new_font
        self.on_disable_popup = on_disable_popup

        super().__init__(
            master,
            title="Font Changed",
            width=400,
            height=220,
            **kwargs
        )

    def _build_content(self) -> None:
        label_font = ctk.CTkFont(size=14)

        ctk.CTkLabel(
            self.content_frame,
            text="Font automatically changed",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(0, 15))

        ctk.CTkLabel(
            self.content_frame,
            text=f"Unicode characters detected in your text.\n\n"
                 f"Font changed from '{self.original_font}'\n"
                 f"to '{self.new_font}' for better symbol support.",
            font=label_font,
            justify="center"
        ).pack(pady=(0, 20))

        # buttons
        btn_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        btn_frame.pack(fill="x")

        if self.on_disable_popup:
            disable_btn = ctk.CTkButton(
                btn_frame,
                text="Don't show again",
                width=130,
                height=36,
                font=ctk.CTkFont(size=13),
                fg_color="transparent",
                border_width=1,
                text_color=("gray30", "gray70"),
                command=self._on_disable
            )
            disable_btn.pack(side="left")

        ok_btn = ctk.CTkButton(
            btn_frame,
            text="OK",
            width=80,
            height=36,
            font=ctk.CTkFont(size=14),
            command=self._on_close
        )
        ok_btn.pack(side="right")

    def _on_disable(self) -> None:
        if self.on_disable_popup:
            self.on_disable_popup()
        self._on_close()
