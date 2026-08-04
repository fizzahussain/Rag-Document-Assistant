import base64
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from pathlib import Path

from fastapi import Header, HTTPException, status

from backend.app.config import settings
from backend.app.core.exceptions import ValidationError

SECRET_KEY = getattr(settings, "POSTGRES_PASSWORD", "rag_secure_secret_key")


def create_access_token(user_id: str, expires_in: int = 86400) -> str:
    """Generates a signed Bearer JWT access token for a user."""
    payload = {
        "sub": str(user_id),
        "exp": int(time.time()) + expires_in,
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"), b64_payload.encode("utf-8"), "sha256"
    ).hexdigest()
    return f"{b64_payload}.{signature}"


def verify_access_token(token: str) -> str:
    """Verifies a Bearer JWT access token signature and expiration, returning user_id."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            raise ValueError("Invalid token format")
        b64_payload, signature = parts
        expected_sig = hmac.new(
            SECRET_KEY.encode("utf-8"), b64_payload.encode("utf-8"), "sha256"
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("Invalid signature")

        padded_b64 = b64_payload + "=" * (-len(b64_payload) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_b64).decode("utf-8"))

        if payload.get("exp", 0) < time.time():
            raise ValueError("Token has expired")

        return payload["sub"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {e!s}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(
    authorization: str | None = Header(None),
    x_user_id: str | None = Header(None),
) -> uuid.UUID:
    """FastAPI dependency to extract and validate the authenticated user ID.

    Checks Bearer token authorization header, X-User-ID header, or falls back to standard dev user.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        user_id_str = verify_access_token(token)
        return uuid.UUID(user_id_str)
    elif x_user_id:
        try:
            return uuid.UUID(x_user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-User-ID header format.",
            )
    else:
        # Development fallback user ID
        return uuid.UUID("00000000-0000-0000-0000-000000000001")


def calculate_sha256(file_bytes: bytes) -> str:
    """Calculates the SHA-256 hash of raw file bytes."""
    return hashlib.sha256(file_bytes).hexdigest()


def sanitize_filename(filename: str) -> str:
    """Sanitizes a user-supplied filename to prevent injection or invalid path characters."""
    filename = os.path.basename(filename)
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
        raise ValidationError(
            "Access denied: Invalid file path traversal attempt detected."
        )
