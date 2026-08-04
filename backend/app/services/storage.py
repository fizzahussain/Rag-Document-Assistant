import os
from pathlib import Path
import uuid
from backend.app.config import settings
from backend.app.core.exceptions import StorageError
from backend.app.core.security import sanitize_filename, verify_path_traversal


class StorageService:
    """Manages file storage on disk, ensuring path traversal prevention and safe unique pathing."""

    def __init__(self, base_dir: str = settings.UPLOAD_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, user_id: str, original_filename: str, content: bytes) -> str:
        """Saves file content to a user-isolated folder with a unique UUID prefix."""
        user_dir = self.base_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        safe_name = sanitize_filename(original_filename)
        unique_filename = f"{uuid.uuid4()}_{safe_name}"
        target_path = str(user_dir / unique_filename)

        verify_path_traversal(str(self.base_dir), target_path)

        try:
            with open(target_path, "wb") as f:
                f.write(content)
            return target_path
        except Exception as e:
            raise StorageError(f"Failed to save file to storage: {str(e)}")

    def delete_file(self, file_path: str) -> None:
        """Deletes a stored file if it exists."""
        if not file_path:
            return
        verify_path_traversal(str(self.base_dir), file_path)
        path = Path(file_path)
        if path.exists():
            try:
                path.unlink()
            except Exception as e:
                raise StorageError(f"Failed to delete file '{file_path}': {str(e)}")

    def read_file(self, file_path: str) -> bytes:
        """Reads file bytes from storage safely."""
        verify_path_traversal(str(self.base_dir), file_path)
        path = Path(file_path)
        if not path.exists():
            raise StorageError(f"File not found on disk: '{file_path}'")
        try:
            with open(path, "rb") as f:
                return f.read()
        except Exception as e:
            raise StorageError(f"Failed to read file from storage: {str(e)}")
