# text area manager for template frame

from typing import Optional, Callable, List
from dataclasses import dataclass

from ...processing.label_renderer import TextAreaConfig
from ...config.defaults import DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE


@dataclass
class TextAreaUIState:
    x: int
    y: int
    font_family: str
    font_size: int
    bold: bool
    italic: bool
    alignment: str
    text: str


class TextAreaManager:
    # manages text areas for the template frame
    # coordinates area lifecycle and position updates from canvas interactions

    def __init__(
        self,
        on_areas_changed: Optional[Callable[[List[str]], None]] = None,
        on_area_selected: Optional[Callable[[int], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ):
        self._text_areas: List[TextAreaConfig] = []
        self._current_area_index: int = -1
        self._on_areas_changed = on_areas_changed
        self._on_area_selected = on_area_selected
        self._on_status = on_status

    @property
    def text_areas(self) -> List[TextAreaConfig]:
        return self._text_areas

    @property
    def current_index(self) -> int:
        return self._current_area_index

    @property
    def current_area(self) -> Optional[TextAreaConfig]:
        if 0 <= self._current_area_index < len(self._text_areas):
            return self._text_areas[self._current_area_index]
        return None

    def add_area(self, area: Optional[TextAreaConfig] = None) -> TextAreaConfig:
        if area is None:
            area_num = len(self._text_areas) + 1
            area = TextAreaConfig(
                name=f"Area {area_num}",
                x=10 + (area_num * 20),
                y=10 + (area_num * 20),
                font_family=DEFAULT_FONT_FAMILY,
                font_size=DEFAULT_FONT_SIZE,
            )

        self._text_areas.append(area)
        self._current_area_index = len(self._text_areas) - 1

        self._notify_areas_changed()
        self._notify_selection_changed()
        self._notify_status(f"Added {area.name}")

        return area

    def remove_current(self) -> bool:
        if not self._text_areas:
            self._notify_status("No text areas to remove")
            return False

        if self._current_area_index < 0:
            return False

        deleted_name = self._text_areas[self._current_area_index].name
        del self._text_areas[self._current_area_index]

        # adjust current index
        if len(self._text_areas) == 0:
            self._current_area_index = -1
        elif self._current_area_index >= len(self._text_areas):
            self._current_area_index = len(self._text_areas) - 1

        self._notify_areas_changed()
        self._notify_selection_changed()
        self._notify_status(f"Removed {deleted_name}")

        return True

    def delete_all(self) -> int:
        if not self._text_areas:
            self._notify_status("No text areas to delete")
            return 0

        count = len(self._text_areas)
        self._text_areas.clear()
        self._current_area_index = -1

        self._notify_areas_changed()
        self._notify_selection_changed()
        self._notify_status(f"Deleted all {count} text areas")

        return count

    def reset_all_text(self) -> None:
        if not self._text_areas:
            self._notify_status("No text areas to reset")
            return

        for area in self._text_areas:
            area.text = ""

        self._notify_selection_changed()
        self._notify_status("Reset all text area contents")

    def select_by_name(self, name: str) -> bool:
        for i, area in enumerate(self._text_areas):
            if area.name == name:
                self._current_area_index = i
                self._notify_selection_changed()
                return True
        return False

    def select_by_index(self, index: int) -> bool:
        if index < 0:
            return False

        if 0 <= index < len(self._text_areas):
            self._current_area_index = index
            self._notify_selection_changed()
            self._notify_status(f"Selected: {self._text_areas[index].name}")
            return True
        return False

    def update_current_from_ui(self, state: TextAreaUIState) -> None:
        if self._current_area_index < 0 or self._current_area_index >= len(self._text_areas):
            return

        area = self._text_areas[self._current_area_index]
        area.x = state.x
        area.y = state.y
        area.font_family = state.font_family
        area.font_size = state.font_size
        area.bold = state.bold
        area.italic = state.italic
        area.alignment = state.alignment
        area.text = state.text

    def get_current_ui_state(self) -> Optional[TextAreaUIState]:
        if self._current_area_index < 0 or self._current_area_index >= len(self._text_areas):
            return None

        area = self._text_areas[self._current_area_index]
        return TextAreaUIState(
            x=area.x,
            y=area.y,
            font_family=area.font_family,
            font_size=area.font_size,
            bold=area.bold,
            italic=area.italic,
            alignment=area.alignment,
            text=area.text
        )

    def on_area_moved(self, index: int, new_x: int, new_y: int) -> None:
        # called from canvas when user drags an area
        if index < 0 or index >= len(self._text_areas):
            return

        self._text_areas[index].x = new_x
        self._text_areas[index].y = new_y

        self._notify_status(f"Moved {self._text_areas[index].name} to ({new_x}, {new_y})")

    def on_area_added(self, new_area: TextAreaConfig) -> None:
        # called from canvas when user pastes an area
        new_area.name = f"Area {len(self._text_areas) + 1}"

        self._text_areas.append(new_area)
        self._current_area_index = len(self._text_areas) - 1

        self._notify_areas_changed()
        self._notify_selection_changed()
        self._notify_status(f"Pasted {new_area.name} at ({new_area.x}, {new_area.y})")

    def get_area_names(self) -> List[str]:
        if not self._text_areas:
            return ["(none)"]
        return [area.name for area in self._text_areas]

    def _notify_areas_changed(self) -> None:
        if self._on_areas_changed:
            self._on_areas_changed(self.get_area_names())

    def _notify_selection_changed(self) -> None:
        if self._on_area_selected:
            self._on_area_selected(self._current_area_index)

    def _notify_status(self, message: str) -> None:
        if self._on_status:
            self._on_status(message)
