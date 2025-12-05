"""manager for template-specific settings persistence"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...gui.interfaces import SettingsService

from ...config.keys import SettingsKeys


class TemplateSettingsManager:
    # manages template specific settings like darkness value
    # provides property based access with automatic persistence

    def __init__(self, settings_service: Optional["SettingsService"] = None):
        from ...config.settings import get_settings
        self._settings = settings_service if settings_service else get_settings()
        self._darkness: float = 1.5

    @property
    def darkness(self) -> float:
        return self._darkness

    @darkness.setter
    def darkness(self, value: float) -> None:
        # clamp to valid range
        self._darkness = max(0.5, min(3.0, value))
        self._save()

    def load(self) -> float:
        self._darkness = self._settings.get(SettingsKeys.Label.DARKNESS, 1.5)
        return self._darkness

    def _save(self) -> None:
        self._settings.set(SettingsKeys.Label.DARKNESS, self._darkness)
        self._settings.save()
