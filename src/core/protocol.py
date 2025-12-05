# ctp500 has fixed 384 pixel width - images must match or be padded
# raster data uses packed bits: 8 pixels per byte, 1=ink (inverted from normal image)

import struct
from typing import Tuple, Type
from PIL import Image

from ..config.defaults import (
    PRINTER_WIDTH_BITS_PER_BYTE,
    PROTOCOL_STATUS_RESPONSE_LENGTH,
    PROTOCOL_MODULO,
)


class PrinterProtocol:
    PRINTER_WIDTH = 384

    CMD_INITIALIZE = b"\x1b\x40"
    CMD_STATUS_REQUEST = b"\x1e\x47\x03"
    CMD_START_PRINT = b"\x1d\x49\xf0\x19"
    CMD_END_PRINT = b"\x9a"
    CMD_RASTER_BITMAP = b"\x1d\x76\x30\x00"

    CMD_LINE_FEED = b"\x0a"
    CMD_CARRIAGE_RETURN = b"\x0d"

    STATUS_RESPONSE_LENGTH = PROTOCOL_STATUS_RESPONSE_LENGTH

    @classmethod
    def build_raster_command(cls: Type["PrinterProtocol"], image: Image.Image) -> bytes:
        width_bytes = image.size[0] // PRINTER_WIDTH_BITS_PER_BYTE
        height = image.size[1]

        command = bytearray(cls.CMD_RASTER_BITMAP)

        # width low byte then high byte
        command.extend(struct.pack('2B', width_bytes % PROTOCOL_MODULO, width_bytes // PROTOCOL_MODULO))

        # height low byte then high byte
        command.extend(struct.pack('2B', height % PROTOCOL_MODULO, height // PROTOCOL_MODULO))

        command.extend(image.tobytes())
        return bytes(command)

    @classmethod
    def calculate_dimensions(cls: Type["PrinterProtocol"], width: int, height: int) -> Tuple[bytes, bytes]:
        w_bytes = width // PRINTER_WIDTH_BITS_PER_BYTE
        width_bytes = struct.pack('2B', w_bytes % PROTOCOL_MODULO, w_bytes // PROTOCOL_MODULO)
        height_bytes = struct.pack('2B', height % PROTOCOL_MODULO, height // PROTOCOL_MODULO)
        return width_bytes, height_bytes

    @classmethod
    def get_line_feeds(cls: Type["PrinterProtocol"], count: int = 1) -> bytes:
        return cls.CMD_LINE_FEED * count
