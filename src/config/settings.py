import logging
import threading
import warnings
from typing import Any, Optional, Dict, List
from pathlib import Path

from .defaults import get_default_config, CONFIG_FILENAME, SETTINGS_SAVE_DELAY
from .settings_validator import SettingsValidator, ValidationResult
from .repository import SettingsRepository, YamlSettingsRepository
from ..core.exceptions import ConfigFileError, InvalidConfigError

logger = logging.getLogger(__name__)


class Settings:
    _SAVE_DELAY = SETTINGS_SAVE_DELAY

    def __init__(
        self,
        config_dir: Optional[str] = None,
        validate: bool = True,
        repository: Optional[SettingsRepository] = None
    ):
        if repository is not None:
            self._repository = repository
        else:
            if config_dir:
                self._config_dir = Path(config_dir)
            else:
                self._config_dir = Path(__file__).parent.parent.parent

            config_path = self._config_dir / CONFIG_FILENAME
            self._repository = YamlSettingsRepository(config_path)

        self._config: Dict[str, Any] = get_default_config()
        self._dirty = False
        self._validate_on_load = validate
        self._fixed_keys: List[str] = []
        self._save_timer: Optional[threading.Timer] = None
        self._lock = threading.RLock()

    @property
    def config_path(self) -> Path:
        if isinstance(self._repository, YamlSettingsRepository):
            return self._repository._config_path
        return Path(f"<{type(self._repository).__name__}>")

    @property
    def repository(self) -> SettingsRepository:
        return self._repository

    @property
    def has_unsaved_changes(self) -> bool:
        with self._lock:
            return self._dirty

    def load(self) -> bool:
        if not self._repository.exists():
            return False

        try:
            loaded = self._repository.load()

            if not loaded:
                loaded = {}

            merged = self._deep_merge(get_default_config(), loaded)

            if self._validate_on_load:
                defaults = get_default_config()
                validated_config, fixed_keys = SettingsValidator.validate_and_fix(
                    merged, defaults
                )

                with self._lock:
                    self._config = validated_config
                    self._fixed_keys = fixed_keys
                    if self._fixed_keys:
                        logger.warning(
                            "Fixed invalid config values: %s", ", ".join(self._fixed_keys)
                        )
                        self._dirty = True
            else:
                with self._lock:
                    self._config = merged
                    self._fixed_keys = []
                    self._dirty = False

            return True

        except ConfigFileError:
            raise

    @property
    def fixed_keys(self) -> List[str]:
        return self._fixed_keys.copy()

    def save(self) -> None:
        with self._lock:
            if self._save_timer is not None:
                self._save_timer.cancel()

            self._save_timer = threading.Timer(self._SAVE_DELAY, self._do_save)
            self._save_timer.daemon = True
            self._save_timer.start()

    def _do_save(self) -> None:
        with self._lock:
            self._save_timer = None
            config_to_save = self._config.copy()

        try:
            self._repository.save(config_to_save)
            with self._lock:
                self._dirty = False

        except ConfigFileError:
            raise

    def save_immediate(self) -> None:
        with self._lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None

        self._do_save()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            keys = key.split('.')
            value = self._config

            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default

            return value

    def set(self, key: str, value: Any, validate: bool = True) -> None:
        if validate:
            is_valid, error = SettingsValidator.validate_setting(key, value)
            if not is_valid:
                raise InvalidConfigError(f"Invalid value for {key}: {error}")

        with self._lock:
            keys = key.split('.')
            config = self._config

            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]

            config[keys[-1]] = value
            self._dirty = True

    def validate(self) -> ValidationResult:
        with self._lock:
            config_copy = self._config.copy()
        return SettingsValidator.validate_config(config_copy)

    def validate_section(self, section: str) -> ValidationResult:
        with self._lock:
            values = self._config.get(section, {})
        return SettingsValidator.validate_section(section, values)

    def get_section(self, section: str) -> Dict[str, Any]:
        with self._lock:
            return self._config.get(section, {}).copy()

    def set_section(self, section: str, values: Dict[str, Any]) -> None:
        with self._lock:
            if section not in self._config:
                self._config[section] = {}
            self._config[section].update(values)
            self._dirty = True

    def reset_to_defaults(self) -> None:
        with self._lock:
            self._config = get_default_config()
            self._dirty = True

    def reset_section(self, section: str) -> None:
        defaults = get_default_config()
        if section in defaults:
            with self._lock:
                self._config[section] = defaults[section].copy()
                self._dirty = True

    @staticmethod
    def _deep_merge(base: Dict, override: Dict) -> Dict:
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Settings._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)


_settings: Optional[Settings] = None


# deprecated - use SettingsFactory.create instead
def get_settings() -> Settings:
    warnings.warn(
        "get_settings() is deprecated. Use SettingsFactory.create() or inject "
        "settings via constructor parameters instead.",
        DeprecationWarning,
        stacklevel=2
    )
    global _settings
    if _settings is None:
        _settings = Settings()
        try:
            _settings.load()
        except ConfigFileError:
            pass
    return _settings


# deprecated - use SettingsFactory.create instead
def reload_settings() -> Settings:
    warnings.warn(
        "reload_settings() is deprecated. Create a new Settings instance instead.",
        DeprecationWarning,
        stacklevel=2
    )
    global _settings
    _settings = Settings()
    _settings.load()
    return _settings


class InMemorySettings:
    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        self._config = initial_data.copy() if initial_data else get_default_config()
        self._dirty = False

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any, validate: bool = True) -> None:
        if validate:
            is_valid, error = SettingsValidator.validate_setting(key, value)
            if not is_valid:
                raise InvalidConfigError(f"Invalid value for {key}: {error}")

        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value
        self._dirty = True

    def get_section(self, section: str) -> Dict[str, Any]:
        return self._config.get(section, {}).copy()

    def set_section(self, section: str, values: Dict[str, Any]) -> None:
        if section not in self._config:
            self._config[section] = {}
        self._config[section].update(values)
        self._dirty = True

    def save(self) -> None:
        self._dirty = False

    def save_immediate(self) -> None:
        self._dirty = False

    @property
    def has_unsaved_changes(self) -> bool:
        return self._dirty


class SettingsFactory:
    @staticmethod
    def create(config_dir: Optional[str] = None) -> Settings:
        settings = Settings(config_dir=config_dir)
        try:
            settings.load()
        except ConfigFileError:
            pass
        return settings

    @staticmethod
    def create_for_testing(initial_data: Optional[Dict[str, Any]] = None) -> InMemorySettings:
        return InMemorySettings(initial_data)
