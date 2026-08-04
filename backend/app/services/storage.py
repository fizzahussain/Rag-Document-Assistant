import hashlib
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

import anyio
from fastapi import UploadFile

from backend.app.config import settings
from backend.app.core.exceptions import StorageError, ValidationError
from backend.app.core.security import sanitize_filename, verify_path_traversal


@dataclass(frozen=True)
class StoredUpload:
    path: str
    size: int
    sha256: str
    original_filename: str


class StorageService:
    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, user_id: str, upload: UploadFile) -> StoredUpload:
        original_filename = sanitize_filename(upload.filename or "unnamed_file")
        user_dir = (self.base_dir / str(user_id)).resolve()
        user_dir.mkdir(parents=True, exist_ok=True)
        target_path = user_dir / f"{uuid.uuid4()}_{original_filename}"
        temporary_path = target_path.with_suffix(target_path.suffix + ".part")
        verify_path_traversal(str(self.base_dir), str(target_path))

        digest = hashlib.sha256()
        total_size = 0
        max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

        try:
            async with await anyio.open_file(temporary_path, "wb") as destination:
                while True:
                    block = await upload.read(settings.UPLOAD_BLOCK_SIZE_BYTES)
                    if not block:
                        break
                    total_size += len(block)
                    if total_size > max_size:
                        raise ValidationError(
                            f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB upload limit"
                        )
                    digest.update(block)
                    await destination.write(block)

            if total_size == 0:
                raise ValidationError("Uploaded file is empty")

            await anyio.to_thread.run_sync(os.replace, temporary_path, target_path)
            return StoredUpload(
                path=str(target_path),
                size=total_size,
                sha256=digest.hexdigest(),
                original_filename=original_filename,
            )
        except Exception:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        finally:
            await upload.close()

    async def read_file(self, file_path: str) -> bytes:
        verify_path_traversal(str(self.base_dir), file_path)
        try:
            return await anyio.Path(file_path).read_bytes()
        except OSError as exc:
            raise StorageError("Failed to read stored file") from exc

    async def delete_file(self, file_path: str) -> None:
        verify_path_traversal(str(self.base_dir), file_path)
        try:
            await anyio.Path(file_path).unlink(missing_ok=True)
        except OSError as exc:
            raise StorageError("Failed to delete stored file") from exc
