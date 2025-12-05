import threading
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable
from time import sleep
from PIL import Image

from .protocol import PrinterProtocol
from .printer import PrinterConnection
from .exceptions import NotConnectedError, PrintError
from ..config.defaults import (
    DEFAULT_CHUNK_SIZE,
    KB_DIVISOR,
    PRINT_PROGRESS_INIT,
    PRINT_PROGRESS_START,
    PRINT_PROGRESS_IMAGE,
    PRINT_PROGRESS_FINISH,
    PRINT_PROGRESS_COMPLETE,
    PRINT_PROGRESS_IMAGE_RANGE,
    PRINT_COMMAND_DELAY_MULTIPLIER,
)

logger = logging.getLogger(__name__)


class JobState(Enum):
    IDLE = "idle"
    PREPARING = "preparing"
    PRINTING = "printing"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PrintJobConfig:
    feed_before: int = 0
    feed_after: int = 0
    command_delay: float = 0.1
    chunk_size: int = DEFAULT_CHUNK_SIZE


@dataclass
class PrintProgress:
    state: JobState
    percentage: int
    message: str
    bytes_sent: int = 0
    total_bytes: int = 0


class PrintJobManager:
    def __init__(self, printer: PrinterConnection):
        self._printer = printer
        self._state = JobState.IDLE
        self._cancel_event = threading.Event()
        self._progress_callback: Optional[Callable[[PrintProgress], None]] = None
        self._completion_callback: Optional[Callable[[bool, str], None]] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> JobState:
        return self._state

    @property
    def is_printing(self) -> bool:
        return self._state in (JobState.PREPARING, JobState.PRINTING)

    def set_progress_callback(
        self, callback: Optional[Callable[[PrintProgress], None]]
    ) -> None:
        self._progress_callback = callback

    def set_completion_callback(
        self, callback: Optional[Callable[[bool, str], None]]
    ) -> None:
        self._completion_callback = callback

    def _report_progress(
        self,
        percentage: int,
        message: str,
        bytes_sent: int = 0,
        total_bytes: int = 0
    ) -> None:
        if self._progress_callback:
            progress = PrintProgress(
                state=self._state,
                percentage=percentage,
                message=message,
                bytes_sent=bytes_sent,
                total_bytes=total_bytes
            )
            try:
                self._progress_callback(progress)
            except Exception as e:
                logger.exception(f"Error in progress callback: {e}")

    def _report_completion(self, success: bool, message: str) -> None:
        if self._completion_callback:
            try:
                self._completion_callback(success, message)
            except Exception as e:
                logger.exception(f"Error in completion callback: {e}")

    def cancel(self) -> bool:
        if not self.is_printing:
            return False

        self._cancel_event.set()
        self._state = JobState.CANCELLING
        return True

    def print_image(
        self,
        image: Image.Image,
        config: Optional[PrintJobConfig] = None,
        blocking: bool = False
    ) -> bool:
        with self._lock:
            if self.is_printing:
                return False

            if not self._printer.is_connected:
                raise NotConnectedError("Not connected to printer")

            self._state = JobState.PREPARING
            self._cancel_event.clear()

        config = config or PrintJobConfig()

        if blocking:
            return self._execute_print_job(image, config)
        else:
            thread = threading.Thread(
                target=self._execute_print_job,
                args=(image, config),
                daemon=True
            )
            thread.start()
            return True

    def _execute_print_job(
        self, image: Image.Image, config: PrintJobConfig
    ) -> bool:
        try:
            if self._cancel_event.is_set():
                self._complete_job(False, "Print cancelled")
                return False

            self._report_progress(PRINT_PROGRESS_INIT, "Initializing...")
            self._printer.initialize()
            sleep(config.command_delay * PRINT_COMMAND_DELAY_MULTIPLIER)

            if self._cancel_event.is_set():
                self._complete_job(False, "Print cancelled")
                return False

            self._state = JobState.PRINTING
            self._report_progress(PRINT_PROGRESS_START, "Starting print...")
            self._printer.start_print()
            sleep(config.command_delay * PRINT_COMMAND_DELAY_MULTIPLIER)

            if config.feed_before > 0:
                self._printer.send_raw(
                    PrinterProtocol.get_line_feeds(config.feed_before)
                )

            if self._cancel_event.is_set():
                self._complete_job(False, "Print cancelled")
                return False

            self._report_progress(PRINT_PROGRESS_IMAGE, "Processing image...")
            raster_cmd = PrinterProtocol.build_raster_command(image)
            total_size = len(raster_cmd)

            if self._cancel_event.is_set():
                self._complete_job(False, "Print cancelled")
                return False

            sent = 0
            while sent < total_size:
                if self._cancel_event.is_set():
                    self._complete_job(False, "Print cancelled")
                    return False

                end = min(sent + config.chunk_size, total_size)
                self._printer.send_raw(raster_cmd[sent:end])
                sent = end

                progress = PRINT_PROGRESS_IMAGE + int((sent / total_size) * PRINT_PROGRESS_IMAGE_RANGE)
                self._report_progress(
                    progress,
                    f"Sending: {sent // KB_DIVISOR}KB / {total_size // KB_DIVISOR}KB",
                    bytes_sent=sent,
                    total_bytes=total_size
                )

            if config.feed_after > 0:
                self._printer.send_raw(
                    PrinterProtocol.get_line_feeds(config.feed_after)
                )

            self._report_progress(PRINT_PROGRESS_FINISH, "Finishing...")
            self._printer.end_print()

            self._report_progress(PRINT_PROGRESS_COMPLETE, "Complete")
            self._complete_job(True, "Print completed successfully")
            return True

        except NotConnectedError:
            self._complete_job(False, "Error: Connection lost")
            return False

        except PrintError as e:
            self._complete_job(False, f"Print error: {e}")
            return False

        except (OSError, ValueError) as e:
            logger.error(f"Unexpected error during print: {e}")
            self._complete_job(False, f"Unexpected error: {e}")
            return False

    def _complete_job(self, success: bool, message: str) -> None:
        self._state = JobState.COMPLETED if success else JobState.FAILED
        self._report_completion(success, message)
        self._state = JobState.IDLE
