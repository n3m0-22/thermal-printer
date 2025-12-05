# calendar generator dialog for printing weekly/monthly calendars
# renders calendars as images for perfect grid alignment

import customtkinter as ctk
from typing import Optional, Callable, List
from datetime import datetime
from PIL import Image

from .centered_dialog import CenteredDialog
from ...processing.calendar_renderer import CalendarRenderer


class CalendarDialog(CenteredDialog):
    def __init__(
        self,
        master,
        on_insert_image: Optional[Callable[[Image.Image], None]] = None,
        **kwargs
    ):
        self.on_insert_image = on_insert_image
        self._month_vars = {}
        self._year_var = None
        self._week_var = None
        self._current_year = datetime.now().year
        self._renderer = CalendarRenderer()

        super().__init__(
            master,
            title="Calendar Generator",
            width=420,
            height=540,
            **kwargs
        )

    def _build_content(self) -> None:
        label_font = ctk.CTkFont(size=14)
        section_font = ctk.CTkFont(size=14, weight="bold")
        btn_font = ctk.CTkFont(size=14)

        # info banner
        info_frame = ctk.CTkFrame(self.content_frame, fg_color=("gray88", "gray22"))
        info_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            info_frame,
            text="Calendars are rendered as images\nfor perfect grid alignment",
            font=ctk.CTkFont(size=15),
            text_color=("gray20", "gray80"),
            justify="center"
        ).pack(pady=10, padx=10)

        # week section
        week_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        week_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            week_frame,
            text="Week",
            font=section_font,
            anchor="w"
        ).pack(fill="x", pady=(0, 5))

        self._week_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            week_frame,
            text="Current Week",
            variable=self._week_var,
            font=label_font,
            command=self._on_selection_change
        ).pack(anchor="w", padx=10)

        # months section
        months_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        months_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            months_frame,
            text=f"Months ({self._current_year})",
            font=section_font,
            anchor="w"
        ).pack(fill="x", pady=(0, 5))

        # grid of month checkboxes 3 columns for compact layout
        month_grid = ctk.CTkFrame(months_frame, fg_color="transparent")
        month_grid.pack(fill="x", padx=10)

        month_names = [
            "January", "February", "March",
            "April", "May", "June",
            "July", "August", "September",
            "October", "November", "December"
        ]

        for i, month_name in enumerate(month_names):
            row = i // 3
            col = i % 3
            var = ctk.BooleanVar(value=False)
            self._month_vars[i + 1] = var

            cb = ctk.CTkCheckBox(
                month_grid,
                text=month_name,
                variable=var,
                font=label_font,
                width=120,
                command=self._on_selection_change
            )
            cb.grid(row=row, column=col, sticky="w", pady=2, padx=5)

        # year section
        year_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        year_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            year_frame,
            text="Full Year",
            font=section_font,
            anchor="w"
        ).pack(fill="x", pady=(0, 5))

        self._year_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            year_frame,
            text=f"All 12 Months ({self._current_year})",
            variable=self._year_var,
            font=label_font,
            command=self._on_year_toggle
        ).pack(anchor="w", padx=10)

        # selection info
        self._selection_label = ctk.CTkLabel(
            self.content_frame,
            text="Select calendars to generate",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("gray30", "gray75")
        )
        self._selection_label.pack(pady=(12, 15))

        # buttons
        btn_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(5, 0))

        close_btn = ctk.CTkButton(
            btn_frame,
            text="Close",
            width=100,
            height=38,
            font=btn_font,
            fg_color="transparent",
            border_width=1,
            text_color=("gray30", "gray70"),
            command=self._on_close
        )
        close_btn.pack(side="left")

        self._insert_btn = ctk.CTkButton(
            btn_frame,
            text="Generate",
            width=120,
            height=38,
            font=btn_font,
            fg_color=("green", "#00AA00"),
            hover_color=("darkgreen", "#008800"),
            command=self._on_generate
        )
        self._insert_btn.pack(side="right")

    def _on_selection_change(self) -> None:
        count = self._count_selections()
        if count == 0:
            self._selection_label.configure(text="Select calendars to generate")
        elif count == 1:
            self._selection_label.configure(text="1 calendar selected")
        else:
            self._selection_label.configure(text=f"{count} calendars selected")

    def _count_selections(self) -> int:
        count = 0
        if self._week_var.get():
            count += 1
        if self._year_var.get():
            count += 12
        else:
            for var in self._month_vars.values():
                if var.get():
                    count += 1
        return count

    def _on_year_toggle(self) -> None:
        # uncheck individual months when full year is selected
        if self._year_var.get():
            for var in self._month_vars.values():
                var.set(False)
        self._on_selection_change()

    def _generate_calendars(self) -> List[Image.Image]:
        images = []

        # week calendar
        if self._week_var.get():
            images.append(self._renderer.render_week())

        # year or individual months
        if self._year_var.get():
            images.extend(self._renderer.render_year(self._current_year))
        else:
            for month, var in self._month_vars.items():
                if var.get():
                    images.append(self._renderer.render_month(self._current_year, month))

        return images

    def _combine_images(self, images: List[Image.Image], spacing: int = 20) -> Image.Image:
        if not images:
            return Image.new('RGB', (384, 100), color=(255, 255, 255))

        if len(images) == 1:
            return images[0]

        # calculate total height
        max_width = max(img.width for img in images)
        total_height = sum(img.height for img in images) + spacing * (len(images) - 1)

        # create combined image
        combined = Image.new('RGB', (max_width, total_height), color=(255, 255, 255))

        y = 0
        for img in images:
            # center horizontally if image is narrower than max width
            x = (max_width - img.width) // 2
            combined.paste(img, (x, y))
            y += img.height + spacing

        return combined

    def _on_generate(self) -> None:
        images = self._generate_calendars()

        if images and self.on_insert_image:
            # combine all images into one
            combined = self._combine_images(images)
            self.on_insert_image(combined)

        self._on_close()
