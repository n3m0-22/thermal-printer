"""component classes extracted from PrinterApp for better separation of concerns
TabManager: tab switching and lazy frame loading
PrintCoordinator: print job management and callbacks
FrameFactory: frame instantiation with dependency injection
"""

from typing import Dict, Any, Type, Optional, Callable
import logging
import customtkinter as ctk
from PIL import Image

from ..core.printer import PrinterConnection
from ..core.print_job import PrintJobManager, PrintJobConfig, PrintProgress
from ..core.exceptions import NotConnectedError

logger = logging.getLogger(__name__)


class TabManager:
    """manages tab switching and frame loading with lazy initialization

    lazy loading creates frames only when tab is first accessed
    caches instances and tracks current frame
    """

    def __init__(
        self,
        frame_classes: Dict[str, Type],
        tabview: ctk.CTkTabview,
        frame_factory: 'FrameFactory',
        on_tab_change: Optional[Callable[[str], None]] = None,
    ):
        self._frame_classes = frame_classes
        self._tabview = tabview
        self._frame_factory = frame_factory
        self._frame_instances: Dict[str, Any] = {}
        self._on_tab_change = on_tab_change

    def ensure_frame_loaded(self, tab_name: str) -> None:
        if tab_name in self._frame_instances:
            return

        frame_class = self._frame_classes.get(tab_name)
        if not frame_class:
            logger.warning(f"Unknown tab: {tab_name}")
            return

        parent = self._tabview.tab(tab_name)
        frame = self._frame_factory.create(frame_class, parent, tab_name=tab_name)

        if frame:
            frame.grid(row=0, column=0, sticky="nsew")
            self._frame_instances[tab_name] = frame
            logger.debug(f"Loaded frame for tab: {tab_name}")

    def get_frame(self, tab_name: str) -> Optional[Any]:
        self.ensure_frame_loaded(tab_name)
        return self._frame_instances.get(tab_name)

    def get_current_frame(self) -> Optional[Any]:
        current_tab = self._tabview.get()
        return self.get_frame(current_tab)

    def on_tab_change(self) -> None:
        current_tab = self._tabview.get()
        self.ensure_frame_loaded(current_tab)

        if self._on_tab_change:
            self._on_tab_change(current_tab)

    def get_loaded_frames(self) -> Dict[str, Any]:
        return self._frame_instances.copy()

    def is_frame_loaded(self, tab_name: str) -> bool:
        return tab_name in self._frame_instances


class PrintCoordinator:
    """coordinates print operations with the print job manager

    handles callbacks for progress reporting and completion
    manages print job execution and connection loss
    """

    def __init__(
        self,
        print_manager: PrintJobManager,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_complete: Optional[Callable[[bool, str], None]] = None,
        on_connection_lost: Optional[Callable[[], None]] = None,
    ):
        self._print_manager = print_manager
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_connection_lost = on_connection_lost
        self._setup_callbacks()

    def _setup_callbacks(self) -> None:
        def on_progress(progress: PrintProgress) -> None:
            if self._on_progress:
                self._on_progress(progress.percentage, progress.message)

        def on_completion(success: bool, message: str) -> None:
            if self._on_complete:
                self._on_complete(success, message)

            if not success and "Connection lost" in message:
                if self._on_connection_lost:
                    self._on_connection_lost()

        self._print_manager.set_progress_callback(on_progress)
        self._print_manager.set_completion_callback(on_completion)

    def print_image(self, image: Image.Image, config: PrintJobConfig) -> None:
        if self._print_manager.is_printing:
            logger.warning("Print requested while already printing")
            return

        self._print_manager.print_image(image, config, blocking=False)

    def cancel_print(self) -> bool:
        return self._print_manager.cancel()

    @property
    def is_printing(self) -> bool:
        return self._print_manager.is_printing


class FrameFactory:
    """factory for creating frame instances with proper dependency injection

    handles frame instantiation with required dependencies and callback wiring
    injects services based on frame type
    """

    def __init__(
        self,
        settings_service,
        printer_service: Optional[PrinterConnection] = None,
        on_print_request: Optional[Callable[[Image.Image], None]] = None,
        on_status_change: Optional[Callable[[str], None]] = None,
        on_scan_request: Optional[Callable[[], None]] = None,
        on_bluetooth_check: Optional[Callable[[], bool]] = None,
    ):
        self._settings = settings_service
        self._printer = printer_service
        self._on_print_request = on_print_request
        self._on_status_change = on_status_change
        self._on_scan_request = on_scan_request
        self._on_bluetooth_check = on_bluetooth_check

    def create(
        self,
        frame_class: Type,
        parent: Any,
        tab_name: Optional[str] = None,
        **kwargs
    ) -> Any:
        try:
            # settings frame has different constructor signature
            if tab_name == "Settings":
                return frame_class(
                    parent,
                    on_status_change=self._on_status_change,
                    settings_service=self._settings,
                    **kwargs
                )

            return frame_class(
                parent,
                on_print_request=self._on_print_request,
                on_status_change=self._on_status_change,
                settings_service=self._settings,
                **kwargs
            )

        except Exception as e:
            logger.error(f"Failed to create frame {frame_class.__name__}: {e}")
            return None
