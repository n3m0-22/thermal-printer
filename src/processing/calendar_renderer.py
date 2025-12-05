# calendar to image rendering for thermal printing
# renders calendars as graphics with perfect grid alignment

from typing import Optional, List
from datetime import datetime, timedelta
import calendar
from PIL import Image, ImageDraw, ImageFont

from ..core.protocol import PrinterProtocol
from ..utils.font_manager import get_font_manager


class CalendarRenderer:

    # thermal printer width
    PRINTER_WIDTH = PrinterProtocol.PRINTER_WIDTH  # 384px

    # calendar dimensions sized for 58mm thermal paper
    CELL_WIDTH = 54  # width of each day cell
    CELL_HEIGHT = 28  # height of each day cell
    HEADER_HEIGHT = 32  # month/year header height
    DAY_HEADER_HEIGHT = 24  # su mo tu row height
    PADDING = 3  # padding inside cells

    def __init__(self, font_size: int = 14):
        self.font_size = font_size
        self._font: Optional[ImageFont.FreeTypeFont] = None
        self._bold_font: Optional[ImageFont.FreeTypeFont] = None
        self._load_fonts()

    def _load_fonts(self) -> None:
        font_manager = get_font_manager()
        # use dejavu sans for good number rendering
        self._font = font_manager.load_font(
            family="DejaVuSans",
            size=self.font_size,
            bold=False,
            italic=False
        )
        self._bold_font = font_manager.load_font(
            family="DejaVuSans",
            size=self.font_size,
            bold=True,
            italic=False
        )

    def render_month(self, year: int, month: int) -> Image.Image:
        cal = calendar.Calendar(firstweekday=6)  # sunday first
        month_name = calendar.month_name[month]
        weeks = cal.monthdayscalendar(year, month)

        # add 1 pixel for right border line
        grid_width = self.CELL_WIDTH * 7
        width = grid_width + 1
        height = (
            self.HEADER_HEIGHT +
            self.DAY_HEADER_HEIGHT +
            self.CELL_HEIGHT * len(weeks) +
            1  # bottom border line
        )

        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        y = 0

        header_text = f"{month_name} {year}"
        self._draw_centered_text(
            draw, header_text, 0, y, grid_width, self.HEADER_HEIGHT,
            font=self._bold_font
        )
        y += self.HEADER_HEIGHT

        draw.line([(0, y), (grid_width, y)], fill=(0, 0, 0), width=1)

        day_abbrevs = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
        for i, abbrev in enumerate(day_abbrevs):
            x = i * self.CELL_WIDTH
            self._draw_centered_text(
                draw, abbrev, x, y, self.CELL_WIDTH, self.DAY_HEADER_HEIGHT,
                font=self._bold_font
            )
        y += self.DAY_HEADER_HEIGHT

        draw.line([(0, y), (grid_width, y)], fill=(0, 0, 0), width=1)

        # includes right border at x=7
        for i in range(8):
            x = i * self.CELL_WIDTH
            line_height = self.HEADER_HEIGHT + self.DAY_HEADER_HEIGHT + self.CELL_HEIGHT * len(weeks)
            draw.line([(x, self.HEADER_HEIGHT), (x, line_height)], fill=(0, 0, 0), width=1)

        for week in weeks:
            for i, day in enumerate(week):
                if day != 0:
                    x = i * self.CELL_WIDTH
                    self._draw_centered_text(
                        draw, str(day), x, y, self.CELL_WIDTH, self.CELL_HEIGHT,
                        font=self._font
                    )
            y += self.CELL_HEIGHT
            draw.line([(0, y), (grid_width, y)], fill=(0, 0, 0), width=1)

        return img

    def render_week(self, date: Optional[datetime] = None) -> Image.Image:
        if date is None:
            date = datetime.now()

        # find sunday that starts the week
        days_since_sunday = (date.weekday() + 1) % 7
        start_of_week = date - timedelta(days=days_since_sunday)
        end_of_week = start_of_week + timedelta(days=6)

        day_abbrevs = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        row_height = 36
        note_area_height = 48  # extra space for notes doubled

        width = self.PRINTER_WIDTH
        height = (
            self.HEADER_HEIGHT +
            (row_height + note_area_height) * 7 +
            2  # bottom border
        )

        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        y = 0

        start_str = start_of_week.strftime("%b %d")
        end_str = end_of_week.strftime("%d")
        year = start_of_week.year
        header_text = f"Week: {start_str}-{end_str}, {year}"

        self._draw_centered_text(
            draw, header_text, 0, y, width, self.HEADER_HEIGHT,
            font=self._bold_font
        )
        y += self.HEADER_HEIGHT

        draw.line([(0, y), (width, y)], fill=(0, 0, 0), width=2)

        for i in range(7):
            day_date = start_of_week + timedelta(days=i)
            day_abbrev = day_abbrevs[i]

            day_text = f"{day_abbrev} {day_date.strftime('%m-%d')}"
            self._draw_left_text(
                draw, day_text, 8, y + 4, font=self._bold_font
            )

            y += row_height

            # no dotted lines for cleaner look
            y += note_area_height

            draw.line([(0, y), (width, y)], fill=(0, 0, 0), width=1)

        return img

    def render_year(self, year: int) -> List[Image.Image]:
        images = []
        for month in range(1, 13):
            images.append(self.render_month(year, month))
        return images

    def _draw_centered_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        width: int,
        height: int,
        font: Optional[ImageFont.FreeTypeFont] = None
    ) -> None:
        if font is None:
            font = self._font

        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # center text in box accounting for baseline offset
        text_x = x + (width - text_width) // 2
        text_y = y + (height - text_height) // 2 - bbox[1]

        draw.text((text_x, text_y), text, fill=(0, 0, 0), font=font)

    def _draw_left_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        font: Optional[ImageFont.FreeTypeFont] = None
    ) -> None:
        if font is None:
            font = self._font
        draw.text((x, y), text, fill=(0, 0, 0), font=font)

    def _draw_dotted_line(
        self,
        draw: ImageDraw.ImageDraw,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        dot_spacing: int = 6
    ) -> None:
        length = x2 - x1
        for i in range(0, length, dot_spacing):
            if i + 2 < length:
                draw.line([(x1 + i, y1), (x1 + i + 2, y2)], fill=(128, 128, 128), width=1)


def render_month_calendar(year: int, month: int, font_size: int = 14) -> Image.Image:
    renderer = CalendarRenderer(font_size=font_size)
    return renderer.render_month(year, month)


def render_week_calendar(date: Optional[datetime] = None, font_size: int = 14) -> Image.Image:
    renderer = CalendarRenderer(font_size=font_size)
    return renderer.render_week(date)
