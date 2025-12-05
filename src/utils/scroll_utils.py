# cross-platform scroll event binding utilities
# handles windows/mac mousewheel and linux button-4/button-5 events

import tkinter as tk
from typing import Optional, Callable, Tuple


# windows and mac use delta/120, linux uses button-4 (up) and button-5 (down)
WINDOWS_MAC_SCROLL_DIVISOR = 120
LINUX_SCROLL_UP = 4
LINUX_SCROLL_DOWN = 5
SCROLL_UNITS_PER_EVENT = 1


def _can_scroll(canvas: tk.Canvas, direction: int) -> bool:
    top, bottom = canvas.yview()

    # if all content is visible, no scrolling needed
    if top == 0.0 and bottom == 1.0:
        return False

    # check boundaries based on direction
    if direction < 0:  # scrolling up
        return top > 0.0
    else:  # scrolling down
        return bottom < 1.0


def _create_scroll_handler_windows_mac(
    canvas: tk.Canvas,
    units_per_scroll: int = SCROLL_UNITS_PER_EVENT
) -> Callable[[tk.Event], str]:
    def on_mousewheel(event: tk.Event) -> str:
        direction = -1 if event.delta > 0 else 1
        if _can_scroll(canvas, direction):
            scroll_amount = int(-1 * (event.delta / WINDOWS_MAC_SCROLL_DIVISOR))
            canvas.yview_scroll(scroll_amount * units_per_scroll, "units")
        return "break"

    return on_mousewheel


def _create_scroll_handler_linux(
    canvas: tk.Canvas,
    units_per_scroll: int = SCROLL_UNITS_PER_EVENT
) -> Callable[[tk.Event], str]:
    def on_mousewheel_linux(event: tk.Event) -> str:
        if event.num == LINUX_SCROLL_UP:
            if _can_scroll(canvas, -1):
                canvas.yview_scroll(-1 * units_per_scroll, "units")
        elif event.num == LINUX_SCROLL_DOWN:
            if _can_scroll(canvas, 1):
                canvas.yview_scroll(1 * units_per_scroll, "units")
        return "break"

    return on_mousewheel_linux


def bind_scroll_events(
    canvas: tk.Canvas,
    *additional_widgets: tk.Widget,
    units_per_scroll: int = SCROLL_UNITS_PER_EVENT,
    add: bool = True
) -> Tuple[Callable, Callable]:
    handler_windows_mac = _create_scroll_handler_windows_mac(canvas, units_per_scroll)
    handler_linux = _create_scroll_handler_linux(canvas, units_per_scroll)

    bind_mode = "+" if add else None

    canvas.bind("<MouseWheel>", handler_windows_mac, add=bind_mode)
    canvas.bind("<Button-4>", handler_linux, add=bind_mode)
    canvas.bind("<Button-5>", handler_linux, add=bind_mode)

    for widget in additional_widgets:
        if widget is not None:
            widget.bind("<MouseWheel>", handler_windows_mac, add=bind_mode)
            widget.bind("<Button-4>", handler_linux, add=bind_mode)
            widget.bind("<Button-5>", handler_linux, add=bind_mode)

    return handler_windows_mac, handler_linux


def unbind_scroll_events(canvas: tk.Canvas, *additional_widgets: tk.Widget) -> None:
    canvas.unbind("<MouseWheel>")
    canvas.unbind("<Button-4>")
    canvas.unbind("<Button-5>")

    for widget in additional_widgets:
        if widget is not None:
            widget.unbind("<MouseWheel>")
            widget.unbind("<Button-4>")
            widget.unbind("<Button-5>")


class ScrollableCanvas:
    def __init__(self, units_per_scroll: int = SCROLL_UNITS_PER_EVENT):
        self._scroll_widgets = []
        self._scroll_handlers = None
        self._units_per_scroll = units_per_scroll

    def setup_scroll_bindings(self) -> None:
        if not isinstance(self, tk.Canvas):
            raise TypeError(
                "ScrollableCanvas must be used with tk.Canvas via "
                "multiple inheritance"
            )

        self._scroll_handlers = bind_scroll_events(
            self,
            *self._scroll_widgets,
            units_per_scroll=self._units_per_scroll
        )

    def add_scroll_widget(self, widget: tk.Widget) -> None:
        if widget is None:
            return

        if widget not in self._scroll_widgets:
            self._scroll_widgets.append(widget)

            if self._scroll_handlers and isinstance(self, tk.Canvas):
                handler_windows_mac, handler_linux = self._scroll_handlers
                widget.bind("<MouseWheel>", handler_windows_mac, add="+")
                widget.bind("<Button-4>", handler_linux, add="+")
                widget.bind("<Button-5>", handler_linux, add="+")

    def remove_scroll_widget(self, widget: tk.Widget) -> None:
        if widget in self._scroll_widgets:
            self._scroll_widgets.remove(widget)
            widget.unbind("<MouseWheel>")
            widget.unbind("<Button-4>")
            widget.unbind("<Button-5>")

    def cleanup_scroll_bindings(self) -> None:
        if isinstance(self, tk.Canvas):
            unbind_scroll_events(self, *self._scroll_widgets)
            self._scroll_widgets.clear()
            self._scroll_handlers = None


def create_scrollable_frame(
    parent: tk.Widget,
    canvas_kwargs: Optional[dict] = None,
    scrollbar_kwargs: Optional[dict] = None
) -> Tuple[tk.Canvas, tk.Frame, tk.Scrollbar]:
    import tkinter.ttk as ttk

    canvas_kwargs = canvas_kwargs or {}
    scrollbar_kwargs = scrollbar_kwargs or {}

    canvas = tk.Canvas(parent, **canvas_kwargs)
    scrollbar = ttk.Scrollbar(parent, command=canvas.yview, **scrollbar_kwargs)
    canvas.configure(yscrollcommand=scrollbar.set)

    interior_frame = tk.Frame(canvas)
    canvas_window = canvas.create_window((0, 0), window=interior_frame, anchor="nw")

    bind_scroll_events(canvas, interior_frame)

    def _configure_interior(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _configure_canvas(event):
        canvas.itemconfig(canvas_window, width=event.width)

    interior_frame.bind("<Configure>", _configure_interior)
    canvas.bind("<Configure>", _configure_canvas)

    return canvas, interior_frame, scrollbar
