import hashlib
import os
import re
from pathlib import Path
from backend.app.core.exceptions import ValidationError


def calculate_sha256(file_bytes: bytes) -> str:
    """Calculates the SHA-256 hash of raw file bytes."""
    return hashlib.sha256(file_bytes).hexdigest()


def sanitize_filename(filename: str) -> str:
    """Sanitizes a user-supplied filename to prevent injection or invalid path characters."""
    # Extract basename to eliminate directory paths sent by the browser/client
    filename = os.path.basename(filename)
    # Remove any characters that are not alphanumeric, dot, underscore, or hyphen
    filename = re.sub(r"[^\w\.\-]", "_", filename)
    return filename or "unnamed_file"


def validate_file_extension(filename: str, allowed_extensions: list[str]) -> str:
    """Validates that the file extension is among the allowed extensions."""
    ext = Path(filename).suffix.lstrip(".").lower()
    if not ext or ext not in [e.lower() for e in allowed_extensions]:
        raise ValidationError(
            f"File extension '.{ext}' is not supported. Allowed extensions: {', '.join(allowed_extensions)}"
        )
    return ext


def validate_file_size(file_bytes: bytes, max_size_mb: int) -> None:
    """Validates that the uploaded file size does not exceed the maximum allowed MB."""
    max_bytes = max_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise ValidationError(
            f"File size ({len(file_bytes) / (1024 * 1024):.2f} MB) exceeds maximum allowed limit of {max_size_mb} MB"
        )


def verify_path_traversal(base_dir: str, target_path: str) -> None:
    """Ensures target_path stays strictly within base_dir to prevent directory traversal attacks."""
    resolved_base = Path(base_dir).resolve()
    resolved_target = Path(target_path).resolve()
    try:
        resolved_target.relative_to(resolved_base)
    except ValueError:
        raise ValidationError("Access denied: Invalid file path traversal attempt detected.")
