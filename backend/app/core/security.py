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


def _auth_secret() -> bytes:
    return settings.AUTH_SECRET_KEY.get_secret_value().encode("utf-8")


def create_access_token(user_id: str, expires_in: int | None = None) -> str:
    payload = {
        "sub": str(user_id),
        "exp": int(time.time())
        + (expires_in if expires_in is not None else settings.ACCESS_TOKEN_TTL_SECONDS),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
    signature = hmac.new(_auth_secret(), encoded_payload.encode("ascii"), "sha256").hexdigest()
    return f"{encoded_payload}.{signature}"


def verify_access_token(token: str) -> str:
    try:
        encoded_payload, signature = token.split(".", maxsplit=1)
        expected_signature = hmac.new(
            _auth_secret(), encoded_payload.encode("ascii"), "sha256"
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError

        padded_payload = encoded_payload + "=" * (-len(encoded_payload) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_payload).decode("utf-8"))
        subject = payload.get("sub")
        expiration = payload.get("exp")
        if not isinstance(subject, str) or not isinstance(expiration, int):
            raise ValueError
        if expiration <= int(time.time()):
            raise ValueError
        return subject
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user_id(
    authorization: str | None = Header(default=None),
) -> uuid.UUID:
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, separator, token = authorization.partition(" ")
    if separator == "" or scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return uuid.UUID(verify_access_token(token))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def calculate_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def sanitize_filename(filename: str) -> str:
    filename = os.path.basename(filename.replace("\\", "/"))
    filename = re.sub(r"[^\w.\-]", "_", filename, flags=re.UNICODE)
    return filename or "unnamed_file"


def validate_file_extension(filename: str, allowed_extensions: list[str]) -> str:
    extension = Path(filename).suffix.lstrip(".").lower()
    allowed = {item.lower() for item in allowed_extensions}
    if not extension or extension not in allowed:
        allowed_extensions = ", ".join(sorted(allowed))

        raise ValidationError(
            f"File extension '.{extension}' is not supported. "
            f"Allowed extensions: {allowed_extensions}"
        )
    return extension


def verify_path_traversal(base_dir: str, target_path: str) -> None:
    base = Path(base_dir).resolve()
    target = Path(target_path).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ValidationError("Invalid file path") from exc
