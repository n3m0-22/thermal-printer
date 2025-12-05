# clipboard utilities with visual feedback

from typing import Optional, Callable
import customtkinter as ctk

from ..config.defaults import FEEDBACK_COPY_RESET_MS, CLIPBOARD_TIMEOUT


def copy_to_clipboard(
    widget: ctk.CTkBaseClass,
    text: str,
    button: Optional[ctk.CTkButton] = None,
    success_text: str = "Copied!",
    error_text: str = "Failed",
    reset_delay_ms: int = FEEDBACK_COPY_RESET_MS
) -> bool:
    try:
        widget.clipboard_clear()
        widget.clipboard_append(text)
        widget.update()  # required for clipboard to persist after window closes

        if button:
            original_text = button.cget("text")
            button.configure(text=success_text)
            widget.after(reset_delay_ms, lambda: _safe_configure(button, text=original_text))

        return True

    except Exception:
        if button:
            original_text = button.cget("text")
            button.configure(text=error_text)
            widget.after(reset_delay_ms, lambda: _safe_configure(button, text=original_text))

        return False


def _safe_configure(widget: ctk.CTkBaseClass, **kwargs) -> None:
    # handles destroyed widgets gracefully
    try:
        widget.configure(**kwargs)
    except Exception:
        pass


def get_from_clipboard(widget: ctk.CTkBaseClass) -> Optional[str]:
    try:
        return widget.clipboard_get()
    except Exception:
        return None


class ClipboardButton(ctk.CTkButton):
    def __init__(
        self,
        master,
        copy_text: Callable[[], str],
        success_text: str = "Copied!",
        error_text: str = "Failed",
        reset_delay_ms: int = FEEDBACK_COPY_RESET_MS,
        **kwargs
    ):
        super().__init__(master, command=self._do_copy, **kwargs)

        self._get_copy_text = copy_text
        self._success_text = success_text
        self._error_text = error_text
        self._reset_delay_ms = reset_delay_ms
        self._original_text = kwargs.get("text", "Copy")

    def _do_copy(self) -> None:
        text = self._get_copy_text()
        if text:
            copy_to_clipboard(
                self,
                text,
                button=self,
                success_text=self._success_text,
                error_text=self._error_text,
                reset_delay_ms=self._reset_delay_ms
            )


def show_copy_feedback(
    widget: ctk.CTkBaseClass,
    label: ctk.CTkLabel,
    success: bool,
    success_text: str = "Copied!",
    error_text: str = "Copy failed",
    original_text: str = "",
    reset_delay_ms: int = FEEDBACK_COPY_RESET_MS
) -> None:
    feedback = success_text if success else error_text
    label.configure(text=feedback)
    widget.after(reset_delay_ms, lambda: _safe_configure(label, text=original_text))
