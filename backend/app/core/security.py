import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from pathlib import Path

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.config import settings
from backend.app.core.exceptions import ValidationError

PASSWORD_MIN_LENGTH = 8
PASSWORD_ITERATIONS = 600_000

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    bearerFormat="Access token",
    description="Enter the access token returned by the login endpoint",
)


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _auth_secret() -> bytes:
    return settings.AUTH_SECRET_KEY.get_secret_value().encode("utf-8")


def create_access_token(
    user_id: str,
    expires_in: int | None = None,
) -> str:
    """Create a signed access token"""

    lifetime = expires_in if expires_in is not None else settings.ACCESS_TOKEN_TTL_SECONDS

    payload = {
        "sub": str(user_id),
        "exp": int(time.time()) + lifetime,
    }

    payload_bytes = json.dumps(
        payload,
        separators=(",", ":"),
    ).encode("utf-8")

    encoded_payload = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")

    signature = hmac.new(
        _auth_secret(),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()

    return f"{encoded_payload}.{signature}"


def verify_access_token(token: str) -> str:
    """Validate an access token and return its subject"""

    try:
        encoded_payload, signature = token.split(".", maxsplit=1)

        if not encoded_payload or not signature:
            raise ValueError("Malformed token")

        expected_signature = hmac.new(
            _auth_secret(),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid token signature")

        padded_payload = encoded_payload + "=" * (-len(encoded_payload) % 4)

        decoded_payload = base64.urlsafe_b64decode(padded_payload)
        payload = json.loads(decoded_payload.decode("utf-8"))

        if not isinstance(payload, dict):
            raise ValueError("Invalid token payload")

        subject = payload.get("sub")
        expiration = payload.get("exp")

        if not isinstance(subject, str) or not subject:
            raise ValueError("Invalid token subject")

        if not isinstance(expiration, int):
            raise ValueError("Invalid token expiration")

        if expiration <= int(time.time()):
            raise ValueError("Expired token")

        return subject

    except (
        ValueError,
        TypeError,
        binascii.Error,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as exc:
        raise _unauthorized("Invalid or expired authentication credentials") from exc


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> uuid.UUID:
    """Return the authenticated user ID"""

    if credentials is None:
        raise _unauthorized("Authentication credentials were not provided")

    if credentials.scheme.lower() != "bearer":
        raise _unauthorized("Invalid authentication scheme")

    token = credentials.credentials.strip()

    if not token:
        raise _unauthorized("Authentication credentials were not provided")

    subject = verify_access_token(token)

    try:
        return uuid.UUID(subject)
    except ValueError as exc:
        raise _unauthorized("Invalid authentication credentials") from exc


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2 and a random salt"""

    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValidationError("Password must be at least 8 characters")

    salt = os.urandom(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )

    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii")

    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${encoded_salt}${encoded_digest}"


def verify_password(
    password: str,
    stored_hash: str,
) -> bool:
    """Verify a password against a PBKDF2 hash"""

    try:
        algorithm, raw_iterations, raw_salt, raw_digest = stored_hash.split("$", 3)

        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(raw_iterations)

        if iterations <= 0 or iterations > 2_000_000:
            return False

        salt = base64.urlsafe_b64decode(raw_salt.encode("ascii"))
        expected_digest = base64.urlsafe_b64decode(raw_digest.encode("ascii"))

        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )

        return hmac.compare_digest(
            actual_digest,
            expected_digest,
        )

    except (
        ValueError,
        TypeError,
        binascii.Error,
        UnicodeEncodeError,
        OverflowError,
    ):
        return False


def calculate_sha256(file_bytes: bytes) -> str:
    """Calculate the SHA-256 digest of file data"""

    return hashlib.sha256(file_bytes).hexdigest()


def sanitize_filename(filename: str) -> str:
    """Return a safe local filename"""

    basename = os.path.basename(filename.replace("\\", "/"))

    sanitized = re.sub(
        r"[^\w.\-]",
        "_",
        basename,
        flags=re.UNICODE,
    )

    return sanitized or "unnamed_file"


def validate_file_extension(
    filename: str,
    allowed_extensions: list[str],
) -> str:
    """Validate and return a lowercase file extension"""

    extension = Path(filename).suffix.lstrip(".").lower()

    allowed = {item.lower().lstrip(".") for item in allowed_extensions}

    if not extension or extension not in allowed:
        allowed_text = ", ".join(sorted(allowed))

        raise ValidationError(
            f"File extension '.{extension}' is not supported. Allowed extensions: {allowed_text}"
        )

    return extension


def verify_path_traversal(
    base_dir: str,
    target_path: str,
) -> None:
    """Verify that a target path remains inside its base directory"""

    base = Path(base_dir).resolve()
    target = Path(target_path).resolve()

    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ValidationError("Invalid file path") from exc
