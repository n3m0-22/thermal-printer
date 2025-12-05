# about dialog with credits and acknowledgments

import customtkinter as ctk
import webbrowser
import re

from .centered_dialog import CenteredDialog


CREDITS_TEXT = """Thermal Printer
Credits and Acknowledgments

This project builds upon the incredible reverse engineering work of the
maker and hacker community who cracked the Core Innovation CTP-500
Bluetooth thermal printer protocol.


ORIGINAL RESEARCH AND DEVELOPMENT

  Mel (ThirtyThreeDown Studio)
    Primary developer of the original CTP500PrinterApp
    Bluetooth protocol analysis and GUI implementation
    https://thirtythreedown.com
    https://github.com/thirtythreedown/CTP500PrinterApp

  voidsshadows
    Creator of CorePrint print server
    Stripped-down Python implementation that formed the foundation
    https://github.com/voidsshadows/CorePrint-print-server


SECKC CONTRIBUTORS
Kansas City's Hacker Hive - https://seckc.org

  bitflip
    Shared critical code resources and collaboration

  Tsathoggualware
    Research and development support

  Reid
    Research and development support


COMMUNITY CONTRIBUTORS

  onezeronull, MaikelChan, rbaron, WerWolv
    Prior thermal printer research and documentation

  Nathaniel (Doodad/Dither Me This)
    Dithering algorithm inspiration

  Hacking Modern Life (YouTube)
    Bluetooth reverse engineering tutorials


SPECIAL THANKS

"To all the mad lasses and lads in the maker community whose thermal
printer research since 2014 made this possible."
  - Mel, ThirtyThreeDown Studio


License: This project is open source.
Original CTP500PrinterApp by ThirtyThreeDown Studio.
CorePrint by voidsshadows (AGPL-3.0)."""


class AboutDialog(CenteredDialog):
    # displays credits and acknowledgments

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            title="About",
            width=600,
            height=650,
            **kwargs
        )

    def _build_content(self) -> None:
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # scrollable text area
        self._text_frame = ctk.CTkScrollableFrame(self.content_frame)
        self._text_frame.grid(row=0, column=0, sticky="nsew")
        self._text_frame.grid_columnconfigure(0, weight=1)

        # build credits with clickable links
        self._build_credits_content()

        self._bind_scroll(self._text_frame)

        # close button
        close_button = ctk.CTkButton(
            self.content_frame,
            text="Close",
            width=120,
            height=40,
            font=ctk.CTkFont(size=14),
            command=self._on_close
        )
        close_button.grid(row=1, column=0, pady=(10, 0))

    def _build_credits_content(self) -> None:
        # url pattern
        url_pattern = re.compile(r'(https?://[^\s]+)')
        row = 0

        for line in CREDITS_TEXT.split('\n'):
            # check if line contains a URL
            match = url_pattern.search(line)

            if match:
                url = match.group(1)
                before = line[:match.start()]
                after = line[match.end():]

                # create frame for this line
                line_frame = ctk.CTkFrame(self._text_frame, fg_color="transparent")
                line_frame.grid(row=row, column=0, sticky="w", padx=15, pady=0)

                if before.strip():
                    ctk.CTkLabel(
                        line_frame,
                        text=before,
                        font=ctk.CTkFont(size=15),
                        anchor="w"
                    ).pack(side="left")

                # clickable link
                link_label = ctk.CTkLabel(
                    line_frame,
                    text=url,
                    font=ctk.CTkFont(size=15),
                    text_color=("#0066CC", "#66B3FF"),
                    cursor="hand2",
                    anchor="w"
                )
                link_label.pack(side="left")
                link_label.bind("<Button-1>", lambda e, u=url: self._open_url(u))
                link_label.bind("<Enter>", lambda e, l=link_label: l.configure(
                    font=ctk.CTkFont(size=15, underline=True)))
                link_label.bind("<Leave>", lambda e, l=link_label: l.configure(
                    font=ctk.CTkFont(size=15, underline=False)))

                if after.strip():
                    ctk.CTkLabel(
                        line_frame,
                        text=after,
                        font=ctk.CTkFont(size=15),
                        anchor="w"
                    ).pack(side="left")
            else:
                # regular text line
                ctk.CTkLabel(
                    self._text_frame,
                    text=line if line else " ",
                    font=ctk.CTkFont(size=15),
                    anchor="w",
                    justify="left"
                ).grid(row=row, column=0, sticky="w", padx=15, pady=0)

            row += 1

    def _open_url(self, url: str) -> None:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    def _bind_scroll(self, scrollable_frame) -> None:
        # bind mouse wheel to scrollable frame with proper boundary enforcement
        canvas = scrollable_frame._parent_canvas

        def can_scroll(direction: int) -> bool:
            # check if scrolling in the given direction is allowed
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
