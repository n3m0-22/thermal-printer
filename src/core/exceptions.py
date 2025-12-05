class PrinterError(Exception):
    pass


class ConnectionError(PrinterError):
    pass


class DisconnectionError(PrinterError):
    pass


class NotConnectedError(PrinterError):
    pass


class AlreadyConnectedError(PrinterError):
    pass


class PrintError(PrinterError):
    pass


class StatusError(PrinterError):
    pass


class BluetoothError(PrinterError):
    pass


class ScanError(BluetoothError):
    pass


class BluetoothScanError(BluetoothError):
    pass


class DeviceNotFoundError(BluetoothError):
    pass


class ConfigurationError(Exception):
    pass


class InvalidConfigError(ConfigurationError):
    pass


class ConfigFileError(ConfigurationError):
    pass


class SettingsLoadError(ConfigurationError):
    pass


class SettingsSaveError(ConfigurationError):
    pass


class ImageProcessingError(Exception):
    pass


class InvalidImageError(ImageProcessingError):
    pass


class ImageLoadError(ImageProcessingError):
    pass


class ImageConversionError(ImageProcessingError):
    pass


class FontError(Exception):
    pass


class FontNotFoundError(FontError):
    pass
