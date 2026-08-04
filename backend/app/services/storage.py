import uuid
from pathlib import Path

import anyio

from backend.app.config import settings
from backend.app.core.exceptions import StorageError
from backend.app.core.security import sanitize_filename, verify_path_traversal


class StorageService:
    """Manages file storage on disk, ensuring path traversal prevention and safe unique pathing."""

    def __init__(self, base_dir: str = settings.UPLOAD_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _sync_write(self, target_path: str, content: bytes) -> None:
        with open(target_path, "wb") as f:
            f.write(content)

    def _sync_read(self, file_path: str) -> bytes:
        with open(file_path, "rb") as f:
            return f.read()

    def _sync_delete(self, file_path: str) -> None:
        path = Path(file_path)
        if path.exists():
            path.unlink()

    async def save_file_async(
        self, user_id: str, original_filename: str, content: bytes
    ) -> str:
        """Saves file content asynchronously using thread pool for non-blocking I/O."""
        user_dir = self.base_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        safe_name = sanitize_filename(original_filename)
        unique_filename = f"{uuid.uuid4()}_{safe_name}"
        target_path = str(user_dir / unique_filename)

        verify_path_traversal(str(self.base_dir), target_path)

        try:
            await anyio.to_thread.run_sync(self._sync_write, target_path, content)
            return target_path
        except Exception as e:
            raise StorageError(f"Failed to save file to storage: {e!s}")

    def save_file(self, user_id: str, original_filename: str, content: bytes) -> str:
        """Saves file content synchronously to a user-isolated folder."""
        user_dir = self.base_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        safe_name = sanitize_filename(original_filename)
        unique_filename = f"{uuid.uuid4()}_{safe_name}"
        target_path = str(user_dir / unique_filename)

        verify_path_traversal(str(self.base_dir), target_path)

        try:
            self._sync_write(target_path, content)
            return target_path
        except Exception as e:
            raise StorageError(f"Failed to save file to storage: {e!s}")

    def delete_file(self, file_path: str) -> None:
        """Deletes a stored file if it exists."""
        if not file_path:
            return
        verify_path_traversal(str(self.base_dir), file_path)
        try:
            self._sync_delete(file_path)
        except Exception as e:
            raise StorageError(f"Failed to delete file '{file_path}': {e!s}")

    def read_file(self, file_path: str) -> bytes:
        """Reads file bytes from storage safely."""
        verify_path_traversal(str(self.base_dir), file_path)
        path = Path(file_path)
        if not path.exists():
            raise StorageError(f"File not found on disk: '{file_path}'")
        try:
            return self._sync_read(file_path)
        except Exception as e:
            raise StorageError(f"Failed to read file from storage: {e!s}")
