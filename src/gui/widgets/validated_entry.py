# validated entry widget with type checking and range validation

from typing import Optional, Callable, Union, Literal
import customtkinter as ctk


class ValidatedEntry(ctk.CTkEntry):
    def __init__(
        self,
        master,
        value_type: Literal["int", "float"] = "int",
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        default: Union[int, float] = 0,
        precision: int = 2,
        on_change: Optional[Callable[[Union[int, float]], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)

        self._value_type = value_type
        self._min_value = min_value
        self._max_value = max_value
        self._default = default
        self._precision = precision
        self._on_change = on_change
        self._last_valid_value = default

        # set initial value
        self._set_display_value(default)

        # bind validation events
        self.bind("<Return>", self._validate_and_apply)
        self.bind("<FocusOut>", self._validate_and_apply)

    def _set_display_value(self, value: Union[int, float]) -> None:
        self.delete(0, "end")
        if self._value_type == "float":
            self.insert(0, f"{value:.{self._precision}f}")
        else:
            self.insert(0, str(int(value)))

    def _validate_and_apply(self, event=None) -> None:
        try:
            raw_value = self.get().strip()

            # parse based on type
            if self._value_type == "float":
                value = float(raw_value)
            else:
                value = int(raw_value)

            # clamp to range
            if self._min_value is not None:
                value = max(self._min_value, value)
            if self._max_value is not None:
                value = min(self._max_value, value)

            # update display with clamped value
            self._set_display_value(value)
            self._last_valid_value = value

            # notify callback
            if self._on_change:
                self._on_change(value)

        except ValueError:
            # reset to last valid value on invalid input
            self._set_display_value(self._last_valid_value)

    def get_value(self) -> Union[int, float]:
        try:
            raw_value = self.get().strip()
            if self._value_type == "float":
                value = float(raw_value)
            else:
                value = int(raw_value)

            # clamp to range
            if self._min_value is not None:
                value = max(self._min_value, value)
            if self._max_value is not None:
                value = min(self._max_value, value)

            return value
        except ValueError:
            return self._last_valid_value

    def set_value(self, value: Union[int, float]) -> None:
        # clamp to range
        if self._min_value is not None:
            value = max(self._min_value, value)
        if self._max_value is not None:
            value = min(self._max_value, value)

        self._set_display_value(value)
        self._last_valid_value = value

    def set_range(
        self,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None
    ) -> None:
        if min_value is not None:
            self._min_value = min_value
        if max_value is not None:
            self._max_value = max_value

        # revalidate current value with new range
        self._validate_and_apply()
