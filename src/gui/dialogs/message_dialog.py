# custom message dialog matching app theme

import customtkinter as ctk
from typing import Optional

from .centered_dialog import CenteredDialog
from ...utils.clipboard import clipboard_set
from ...config.defaults import (
    DIALOG_BUTTON_SMALL_WIDTH,
    DIALOG_BUTTON_HEIGHT,
    ICON_COLOR_ERROR,
    ICON_COLOR_WARNING,
    ICON_COLOR_INFO,
    ICON_COLOR_SUCCESS,
    ICON_COLOR_QUESTION,
    FEEDBACK_COPY_RESET_MS,
)
from ..theme import AppFonts


class MessageDialog(CenteredDialog):
    # custom message dialog for errors, warnings, and info messages

    def __init__(
        self,
        master,
        title: str = "Message",
        message: str = "",
        icon: str = "info",
        show_copy: bool = True,
        **kwargs
    ):
        self._message = message
        self._icon = icon
        self._show_copy = show_copy
        self._copy_button: Optional[ctk.CTkButton] = None

        # estimate dialog size based on message length
        msg_lines = message.count('\n') + 1
        msg_width = min(max(len(message) * 7, 400), 500)
        msg_height = min(180 + msg_lines * 20, 400)

        super().__init__(
            master,
            title=title,
            width=msg_width,
            height=msg_height,
            **kwargs
        )

        # bind keys
        self.bind("<Return>", lambda e: self._on_close())
        self.bind("<Escape>", lambda e: self._on_close())
        self.bind("<Control-c>", lambda e: self._copy_to_clipboard())

    def _build_content(self) -> None:
        # icon and title row
        header = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))

        icon_label = ctk.CTkLabel(
            header,
            text=self._get_icon_text(),
            font=ctk.CTkFont(size=32),
            text_color=self._get_icon_color(),
            width=50
        )
        icon_label.pack(side="left", padx=(0, 10))

        title_label = ctk.CTkLabel(
            header,
            text=self._dialog_title,
            font=AppFonts.title(),
            anchor="w"
        )
        title_label.pack(side="left", fill="x", expand=True)

        # message text
        message_label = ctk.CTkLabel(
            self.content_frame,
            text=self._message,
            font=AppFonts.normal(),
            justify="left",
            anchor="w",
            wraplength=350
        )
        message_label.pack(fill="x", pady=(0, 20))

        # button row
        button_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        button_frame.pack()

        if self._show_copy:
            self._copy_button = ctk.CTkButton(
                button_frame,
                text="Copy",
                width=DIALOG_BUTTON_SMALL_WIDTH,
                height=DIALOG_BUTTON_HEIGHT,
                font=AppFonts.button(),
                fg_color="transparent",
                border_width=1,
                text_color=("gray10", "gray90"),
                command=self._copy_to_clipboard
            )
            self._copy_button.pack(side="left", padx=(0, 10))

        ok_button = ctk.CTkButton(
            button_frame,
            text="OK",
            width=DIALOG_BUTTON_SMALL_WIDTH,
            height=DIALOG_BUTTON_HEIGHT,
            font=AppFonts.button(),
            command=self._on_close
        )
        ok_button.pack(side="left")

    def _get_icon_text(self) -> str:
        # return unicode symbol for icon type
        icons = {
            "error": "\u2716",      # heavy x
            "warning": "\u26A0",    # warning triangle
            "info": "\u2139",       # info symbol
            "success": "\u2714",    # check mark
            "question": "?",        # question mark
        }
        return icons.get(self._icon, "\u2139")

    def _get_icon_color(self) -> str:
        # return color for icon type
        colors = {
            "error": ICON_COLOR_ERROR,
            "warning": ICON_COLOR_WARNING,
            "info": ICON_COLOR_INFO,
            "success": ICON_COLOR_SUCCESS,
            "question": ICON_COLOR_QUESTION,
        }
        return colors.get(self._icon, ICON_COLOR_INFO)

    def _copy_to_clipboard(self) -> None:
        # copy title and message to clipboard
        text = f"{self._dialog_title}\n\n{self._message}"
        success = clipboard_set(text)

        if self._copy_button:
            if success:
                original_text = self._copy_button.cget("text")
                self._copy_button.configure(text="Copied!")
                self.after(FEEDBACK_COPY_RESET_MS, lambda: self._copy_button.configure(text=original_text))
            else:
                self._copy_button.configure(text="Failed")
                self.after(FEEDBACK_COPY_RESET_MS, lambda: self._copy_button.configure(text="Copy"))


class ConfirmDialog(CenteredDialog):
    # confirmation dialog with yes/no buttons

    def __init__(
        self,
        master,
        title: str = "Confirm",
        message: str = "",
        icon: str = "question",
        yes_text: str = "Yes",
        no_text: str = "No",
        **kwargs
    ):
        self._message = message
        self._icon = icon
        self._yes_text = yes_text
        self._no_text = no_text
        self._result: bool = False

        # estimate dialog size based on message length
        msg_lines = message.count('\n') + 1
        msg_width = min(max(len(message) * 7, 400), 500)
        msg_height = min(180 + msg_lines * 20, 400)

        super().__init__(
            master,
            title=title,
            width=msg_width,
            height=msg_height,
            **kwargs
        )

        # bind keys
        self.bind("<Escape>", lambda e: self._on_no())
        self.bind("<Return>", lambda e: self._on_yes())

    @property
    def result(self) -> bool:
        return self._result

    def _build_content(self) -> None:
        # icon and title row
        header = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))

        icon_label = ctk.CTkLabel(
            header,
            text=self._get_icon_text(),
            font=ctk.CTkFont(size=32),
            text_color=self._get_icon_color(),
            width=50
        )
        icon_label.pack(side="left", padx=(0, 10))

        title_label = ctk.CTkLabel(
            header,
            text=self._dialog_title,
            font=AppFonts.title(),
            anchor="w"
        )
        title_label.pack(side="left", fill="x", expand=True)

        # message text
        message_label = ctk.CTkLabel(
            self.content_frame,
            text=self._message,
            font=AppFonts.normal(),
            justify="left",
            anchor="w",
            wraplength=350
        )
        message_label.pack(fill="x", pady=(0, 20))

        # button row
        button_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        button_frame.pack()

        no_button = ctk.CTkButton(
            button_frame,
            text=self._no_text,
            width=DIALOG_BUTTON_SMALL_WIDTH,
            height=DIALOG_BUTTON_HEIGHT,
            font=AppFonts.button(),
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self._on_no
        )
        no_button.pack(side="left", padx=(0, 10))

        yes_button = ctk.CTkButton(
            button_frame,
            text=self._yes_text,
            width=DIALOG_BUTTON_SMALL_WIDTH,
            height=DIALOG_BUTTON_HEIGHT,
            font=AppFonts.button(),
            command=self._on_yes
        )
        yes_button.pack(side="left")

    def _get_icon_text(self) -> str:
        icons = {
            "error": "\u2716",
            "warning": "\u26A0",
            "info": "\u2139",
            "success": "\u2714",
            "question": "?",
        }
        return icons.get(self._icon, "?")

    def _get_icon_color(self) -> str:
        colors = {
            "error": ICON_COLOR_ERROR,
            "warning": ICON_COLOR_WARNING,
            "info": ICON_COLOR_INFO,
            "success": ICON_COLOR_SUCCESS,
            "question": ICON_COLOR_QUESTION,
        }
        return colors.get(self._icon, ICON_COLOR_QUESTION)

    def _on_yes(self) -> None:
        self._result = True
        self._on_close()

    def _on_no(self) -> None:
        self._result = False
        self._on_close()


def show_error(master, title: str, message: str, show_copy: bool = True) -> None:
    # show error dialog
    dialog = MessageDialog(master, title=title, message=message, icon="error", show_copy=show_copy)
    dialog.wait_window()


def show_warning(master, title: str, message: str, show_copy: bool = True) -> None:
    # show warning dialog
    dialog = MessageDialog(master, title=title, message=message, icon="warning", show_copy=show_copy)
    dialog.wait_window()


def show_info(master, title: str, message: str, show_copy: bool = False) -> None:
    # show info dialog
    dialog = MessageDialog(master, title=title, message=message, icon="info", show_copy=show_copy)
    dialog.wait_window()


def show_success(master, title: str, message: str, show_copy: bool = False) -> None:
    # show success dialog
    dialog = MessageDialog(master, title=title, message=message, icon="success", show_copy=show_copy)
    dialog.wait_window()


def ask_yes_no(
    master,
    title: str,
    message: str,
    icon: str = "question",
    yes_text: str = "Yes",
    no_text: str = "No"
) -> bool:
    # show confirmation dialog and return true if yes was clicked
    dialog = ConfirmDialog(
        master,
        title=title,
        message=message,
        icon=icon,
        yes_text=yes_text,
        no_text=no_text
    )
    dialog.wait_window()
    return dialog.result
