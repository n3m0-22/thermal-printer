# reusable mixins for common frame patterns

from typing import Optional, Tuple, List
from PIL import Image
import os


class PreviewMixin:

    def _update_preview(self, image: Image.Image) -> None:
        if hasattr(self, 'preview_canvas') and self.preview_canvas:
            self.preview_canvas.set_image(image)

    def _clear_preview(self) -> None:
        if hasattr(self, 'preview_canvas') and self.preview_canvas:
            self.preview_canvas.clear()

    def _get_preview_size(self) -> Tuple[int, int]:
        if hasattr(self, 'preview_canvas') and self.preview_canvas:
            return (
                self.preview_canvas.winfo_width(),
                self.preview_canvas.winfo_height()
            )
        return (0, 0)

    @property
    def preview_canvas(self):
        return getattr(self, '_preview_canvas', None)


class FileDialogMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_directory: Optional[str] = None

    def _open_file_dialog(
        self,
        filetypes: List[Tuple[str, str]],
        title: str = "Open"
    ) -> Optional[str]:
        from src.utils.file_dialogs import open_file_dialog

        initial_dir = self._get_last_directory()
        filepath = open_file_dialog(
            title=title,
            filetypes=filetypes,
            initialdir=initial_dir
        )

        if filepath:
            self._save_last_directory(filepath)

        return filepath

    def _save_file_dialog(
        self,
        filetypes: List[Tuple[str, str]],
        title: str = "Save",
        defaultextension: str = ""
    ) -> Optional[str]:
        from src.utils.file_dialogs import save_file_dialog

        initial_dir = self._get_last_directory()
        filepath = save_file_dialog(
            title=title,
            filetypes=filetypes,
            defaultextension=defaultextension,
            initialdir=initial_dir
        )

        if filepath:
            self._save_last_directory(filepath)

        return filepath

    def _get_last_directory(self) -> str:
        if self._last_directory and os.path.isdir(self._last_directory):
            return self._last_directory
        return ""

    def _save_last_directory(self, filepath: str) -> None:
        if filepath:
            self._last_directory = os.path.dirname(filepath)


class SaveLoadMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_modified: bool = False
        self._loaded_filepath: Optional[str] = None

    def _mark_modified(self) -> None:
        self._is_modified = True

    def _clear_modified(self) -> None:
        self._is_modified = False

    @property
    def is_modified(self) -> bool:
        return self._is_modified

    def _confirm_discard_changes(self) -> bool:
        if not self._is_modified:
            return True

        # import here to avoid circular dependency
        from src.gui.dialogs.message_dialog import MessageDialog

        result = MessageDialog(
            self.winfo_toplevel(),
            title="Unsaved Changes",
            message="You have unsaved changes. Discard them?",
            buttons=["Discard", "Cancel"]
        ).show()

        return result == "Discard"

    def _set_loaded_filepath(self, filepath: Optional[str]) -> None:
        self._loaded_filepath = filepath

    def _get_loaded_filepath(self) -> Optional[str]:
        return self._loaded_filepath
