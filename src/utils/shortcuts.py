# keyboard shortcut binding utilities for text widgets
# uses custom clipboard module to handle wayland vs x11 properly
# tkinter event handlers return break to prevent default behavior

import tkinter as tk
from typing import Any, Callable, Optional, Literal

from .clipboard import clipboard_get, clipboard_set
from ..config.defaults import WIDGET_CHANGE_DELAY_MS


def _create_clipboard_handlers(
    widget: Any,
    target: Any,
    widget_type: Literal["entry", "text"],
    on_change: Optional[Callable] = None
) -> tuple:
    is_entry = widget_type == "entry"

    def select_all(event=None):
        if is_entry:
            target.select_range(0, "end")
            target.icursor("end")
        else:
            target.tag_add("sel", "1.0", "end-1c")
            target.mark_set("insert", "end-1c")
        return "break"

    def paste_text(event=None):
        text = clipboard_get()
        if text:
            try:
                if is_entry:
                    if target.selection_present():
                        target.delete("sel.first", "sel.last")
                else:
                    target.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
            target.insert("insert", text)
            if on_change:
                widget.after(WIDGET_CHANGE_DELAY_MS, on_change)
        return "break"

    def copy_text(event=None):
        try:
            if is_entry:
                if target.selection_present():
                    text = target.selection_get()
                    if text:
                        clipboard_set(text)
            else:
                text = target.get("sel.first", "sel.last")
                if text:
                    clipboard_set(text)
        except tk.TclError:
            pass
        return "break"

    def cut_text(event=None):
        try:
            if is_entry:
                if target.selection_present():
                    text = target.selection_get()
                    if text:
                        clipboard_set(text)
                        target.delete("sel.first", "sel.last")
                        if on_change:
                            widget.after(WIDGET_CHANGE_DELAY_MS, on_change)
            else:
                text = target.get("sel.first", "sel.last")
                if text:
                    clipboard_set(text)
                    target.delete("sel.first", "sel.last")
                    if on_change:
                        widget.after(WIDGET_CHANGE_DELAY_MS, on_change)
        except tk.TclError:
            pass
        return "break"

    return select_all, paste_text, copy_text, cut_text


def _bind_common_shortcuts(
    target: Any,
    select_all: Callable,
    paste_text: Callable,
    copy_text: Callable,
    cut_text: Callable
) -> None:
    # both uppercase and lowercase to handle caps lock
    target.bind("<Control-a>", select_all)
    target.bind("<Control-A>", select_all)
    target.bind("<Control-v>", paste_text)
    target.bind("<Control-V>", paste_text)
    target.bind("<Control-c>", copy_text)
    target.bind("<Control-C>", copy_text)
    target.bind("<Control-x>", cut_text)
    target.bind("<Control-X>", cut_text)

    # override tk default clipboard to use our wayland/x11 aware version
    target.bind("<<Copy>>", copy_text)
    target.bind("<<Cut>>", cut_text)
    target.bind("<<Paste>>", paste_text)
    target.bind("<<SelectAll>>", select_all)


def bind_entry_shortcuts(
    widget: Any,
    entry_widget: Any,
    on_change: Optional[Callable] = None
) -> None:
    # ctkentry wraps tk entry in _entry attribute
    entry = getattr(entry_widget, '_entry', entry_widget)

    select_all, paste_text, copy_text, cut_text = _create_clipboard_handlers(
        widget, entry, "entry", on_change
    )
    _bind_common_shortcuts(entry, select_all, paste_text, copy_text, cut_text)


def bind_text_shortcuts(
    widget: Any,
    textbox: Any,
    on_change: Optional[Callable] = None
) -> None:
    select_all, paste_text, copy_text, cut_text = _create_clipboard_handlers(
        widget, textbox, "text", on_change
    )
    _bind_common_shortcuts(textbox, select_all, paste_text, copy_text, cut_text)

    def undo_text(event=None):
        try:
            textbox.edit_undo()
        except tk.TclError:
            pass
        return "break"

    def redo_text(event=None):
        try:
            textbox.edit_redo()
        except tk.TclError:
            pass
        return "break"

    textbox.bind("<Control-z>", undo_text)
    textbox.bind("<Control-Z>", undo_text)
    textbox.bind("<Control-y>", redo_text)
    textbox.bind("<Control-Y>", redo_text)
