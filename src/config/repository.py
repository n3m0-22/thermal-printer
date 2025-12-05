import logging
from abc import abstractmethod
from pathlib import Path
from typing import Any, Dict, Protocol

import yaml

from ..core.exceptions import ConfigFileError

logger = logging.getLogger(__name__)


class SettingsRepository(Protocol):
    def load(self) -> Dict[str, Any]:
        ...

    def save(self, data: Dict[str, Any]) -> None:
        ...

    def exists(self) -> bool:
        ...

    def delete(self) -> None:
        ...


class YamlSettingsRepository:
    def __init__(self, config_path: Path):
        self._config_path = Path(config_path)

    def load(self) -> Dict[str, Any]:
        if not self._config_path.exists():
            return {}

        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                loaded = yaml.safe_load(f)

            if loaded is None:
                return {}

            if not isinstance(loaded, dict):
                raise ConfigFileError(
                    f"Invalid YAML structure: expected dict, got {type(loaded).__name__}"
                )

            return loaded

        except yaml.YAMLError as e:
            raise ConfigFileError(f"Invalid YAML in config file: {e}")
        except IOError as e:
            raise ConfigFileError(f"Cannot read config file: {e}")

    def save(self, data: Dict[str, Any]) -> None:
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self._config_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    data,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True
                )

            logger.debug("Settings saved to %s", self._config_path)

        except IOError as e:
            logger.error("Failed to save settings: %s", e)
            raise ConfigFileError(f"Cannot write config file: {e}")

    def exists(self) -> bool:
        return self._config_path.exists() and self._config_path.is_file()

    def delete(self) -> None:
        if not self._config_path.exists():
            return

        try:
            self._config_path.unlink()
            logger.debug("Settings file deleted: %s", self._config_path)
        except IOError as e:
            raise ConfigFileError(f"Cannot delete config file: {e}")


class InMemorySettingsRepository:
    def __init__(self, initial_data: Dict[str, Any] | None = None):
        self._data: Dict[str, Any] = initial_data.copy() if initial_data else {}
        self._exists = bool(initial_data)

    def load(self) -> Dict[str, Any]:
        return self._data.copy()

    def save(self, data: Dict[str, Any]) -> None:
        self._data = data.copy()
        self._exists = True
        logger.debug("Settings saved to memory")

    def exists(self) -> bool:
        return self._exists

    def delete(self) -> None:
        self._data = {}
        self._exists = False
        logger.debug("Settings cleared from memory")
