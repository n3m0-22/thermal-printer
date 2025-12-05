# font selector widget with searchable popup list

import tkinter as tk
from typing import Optional, Callable, List
import customtkinter as ctk

from ...utils.shortcuts import bind_entry_shortcuts


class FontSelector(ctk.CTkFrame):

    MIN_WIDTH = 250
    MIN_HEIGHT = 300

    def __init__(
        self,
        master,
        fonts: List[str],
        command: Optional[Callable[[str], None]] = None,
        width: int = 180,
        height: int = 36,
        recommended_fonts: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._fonts = fonts
        self._filtered_fonts = fonts.copy()
        self._command = command
        self._recommended_fonts = recommended_fonts or []
        self._popup: Optional[ctk.CTkToplevel] = None
        self._selected_font = fonts[0] if fonts else "Default"
        self._highlighted_font: Optional[str] = None
        self._popup_width = 340
        self._popup_height = 450

        self.select_button = ctk.CTkButton(
            self,
            text=self._selected_font,
            width=width,
            height=height,
            font=ctk.CTkFont(size=14),
            anchor="w",
            command=self._show_popup
        )
        self.select_button.pack(fill="x")

    @property
    def font_name(self) -> str:
        return self._selected_font

    def set(self, font_name: str) -> None:
        if font_name in self._fonts:
            self._selected_font = font_name
            self.select_button.configure(text=font_name)

    def get(self) -> str:
        return self._selected_font

    def _make_modal(self) -> None:
        if self._popup and self._popup.winfo_exists():
            try:
                self._popup.grab_set()
                self._popup.focus_force()
            except tk.TclError:
                self._popup.after(50, self._make_modal)

    def _center_and_show_popup(self) -> None:
        if self._popup and self._popup.winfo_exists():
            # ensure geometry is calculated
            self._main_window.update_idletasks()
            self._popup.update_idletasks()

            parent_x = self._main_window.winfo_x()
            parent_y = self._main_window.winfo_y()
            parent_width = self._main_window.winfo_width()
            parent_height = self._main_window.winfo_height()

            # calculate center position
            x = parent_x + (parent_width - self._popup_width) // 2
            y = parent_y + (parent_height - self._popup_height) // 2

            # ensure popup stays on screen
            screen_width = self._popup.winfo_screenwidth()
            screen_height = self._popup.winfo_screenheight()
            x = max(0, min(x, screen_width - self._popup_width))
            y = max(0, min(y, screen_height - self._popup_height))

            # store for delayed positioning
            self._target_x = x
            self._target_y = y

            # set size and show
            self._popup.geometry(f"{self._popup_width}x{self._popup_height}")
            self._popup.deiconify()
            self._popup.update_idletasks()

            # set position after short delay (Wayland compositor needs time)
            self._popup.after(50, self._apply_popup_position)

    def _apply_popup_position(self) -> None:
        if self._popup and self._popup.winfo_exists():
            self._popup.geometry(f"+{self._target_x}+{self._target_y}")
            self._popup.update_idletasks()
            # make modal after positioning
            self._popup.after(10, self._make_modal)

    def _show_popup(self) -> None:
        if self._popup is not None and self._popup.winfo_exists():
            self._popup.destroy()
            self._popup = None
            return

        # store reference to main window for centering
        self._main_window = self.winfo_toplevel()

        self._popup = ctk.CTkToplevel(self)

        # hide until positioned
        self._popup.withdraw()

        # transient for proper parent relationship and wayland compatibility
        self._popup.transient(self._main_window)

        # set window title shown in wm title bar
        self._popup.title("Select Font")

        # splash type helps with positioning on wayland
        try:
            self._popup.attributes('-type', 'splash')
        except tk.TclError:
            pass

        # configure resizable with minimum size
        self._popup.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)

        # handle WM close button
        self._popup.protocol("WM_DELETE_WINDOW", self._close_popup)

        # main content frame
        main_frame = ctk.CTkFrame(
            self._popup,
            fg_color=("gray95", "gray14"),
            corner_radius=0
        )
        main_frame.pack(fill="both", expand=True)

        # content area
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # search entry
        search_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        search_frame.pack(fill="x", pady=(0, 10))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._filter_fonts)

        search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search fonts...",
            textvariable=self._search_var,
            font=ctk.CTkFont(size=15),
            height=36
        )
        search_entry.pack(fill="x")
        search_entry.focus()

        # bind keyboard shortcuts
        bind_entry_shortcuts(self._popup, search_entry)

        # scrollable font list
        self._font_list_frame = ctk.CTkScrollableFrame(content_frame)
        self._font_list_frame.pack(fill="both", expand=True, pady=(0, 10))

        self._bind_scroll(self._font_list_frame)
        self._populate_font_list()

        # buttons
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.pack(fill="x")

        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            width=100,
            height=36,
            font=ctk.CTkFont(size=14),
            command=self._close_popup
        )
        close_button.pack(side="left")

        select_button = ctk.CTkButton(
            button_frame,
            text="Select",
            width=100,
            height=36,
            font=ctk.CTkFont(size=14),
            command=self._select_current
        )
        select_button.pack(side="right")

        self._popup.bind("<Escape>", lambda e: self._close_popup())

        # center and show after setup is complete
        self._popup.after(10, self._center_and_show_popup)

    def _filter_fonts(self, *args) -> None:
        search = self._search_var.get().lower()
        if search:
            self._filtered_fonts = [f for f in self._fonts if search in f.lower()]
        else:
            self._filtered_fonts = self._fonts.copy()
        self._populate_font_list()

    def _is_recommended(self, font: str) -> bool:
        """Check if font matches any recommended font pattern."""
        if not self._recommended_fonts:
            return False
        font_lower = font.lower()
        return any(rec.lower() in font_lower for rec in self._recommended_fonts)

    def _populate_font_list(self) -> None:
        for widget in self._font_list_frame.winfo_children():
            widget.destroy()

        self._font_buttons = {}

        # sort with recommended fonts first if we have recommendations
        if self._recommended_fonts:
            recommended = [f for f in self._filtered_fonts if self._is_recommended(f)]
            others = [f for f in self._filtered_fonts if not self._is_recommended(f)]
            sorted_fonts = recommended + others
        else:
            sorted_fonts = self._filtered_fonts

        # limit for performance
        for font in sorted_fonts[:100]:
            # add star prefix for recommended fonts
            display_text = f"★ {font}" if self._is_recommended(font) else font

            btn = ctk.CTkButton(
                self._font_list_frame,
                text=display_text,
                anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray30"),
                font=ctk.CTkFont(size=15),
                height=32,
                command=lambda f=font: self._highlight_font(f)
            )
            btn.pack(fill="x", pady=2)
            btn.bind("<Double-Button-1>", lambda e, f=font: self._select_font(f))
            self._font_buttons[font] = btn

            # highlight currently selected or highlighted font
            if font == self._highlighted_font or (self._highlighted_font is None and font == self._selected_font):
                btn.configure(fg_color=("gray70", "gray40"))

        # rebind scroll to newly created widgets
        if hasattr(self, '_scroll_bind_func'):
            self._popup.after(50, lambda: self._scroll_bind_func(self._font_list_frame))

    def _highlight_font(self, font: str) -> None:
        # unhighlight previous
        if self._highlighted_font and self._highlighted_font in self._font_buttons:
            self._font_buttons[self._highlighted_font].configure(fg_color="transparent")

        # highlight new
        self._highlighted_font = font
        if font in self._font_buttons:
            self._font_buttons[font].configure(fg_color=("gray70", "gray40"))

    def _select_current(self) -> None:
        font = self._highlighted_font if self._highlighted_font else self._selected_font
        self._select_font(font)

    def _select_font(self, font: str) -> None:
        self._selected_font = font
        self._highlighted_font = None
        self.select_button.configure(text=font)
        self._close_popup()

        if self._command:
            self._command(font)

    def _bind_scroll(self, scrollable_frame) -> None:
        # bind mouse wheel to scrollable frame with proper boundary enforcement
        canvas = scrollable_frame._parent_canvas

        def can_scroll(direction: int) -> bool:
            """Check if scrolling in the given direction is allowed."""
            top, bottom = canvas.yview()
            if top == 0.0 and bottom == 1.0:
                return False
            if direction < 0:
                return top > 0.0
            else:
                return bottom < 1.0

        def on_mousewheel(event):
            direction = -1 if event.delta > 0 else 1
            if can_scroll(direction):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        def on_mousewheel_linux(event):
            if event.num == 4:
                if can_scroll(-1):
                    canvas.yview_scroll(-3, "units")
            elif event.num == 5:
                if can_scroll(1):
                    canvas.yview_scroll(3, "units")
            return "break"

        def bind_to_widget(widget):
            widget.bind("<MouseWheel>", on_mousewheel, add="+")
            widget.bind("<Button-4>", on_mousewheel_linux, add="+")
            widget.bind("<Button-5>", on_mousewheel_linux, add="+")
            for child in widget.winfo_children():
                bind_to_widget(child)

        canvas.bind("<MouseWheel>", on_mousewheel, add="+")
        canvas.bind("<Button-4>", on_mousewheel_linux, add="+")
        canvas.bind("<Button-5>", on_mousewheel_linux, add="+")
        bind_to_widget(scrollable_frame)

        # store for rebinding after populate
        self._scroll_bind_func = bind_to_widget

    def _close_popup(self) -> None:
        if self._popup and self._popup.winfo_exists():
            try:
                self._popup.grab_release()
            except tk.TclError:
                pass
            self._popup.destroy()
        self._popup = None
        self._highlighted_font = None
