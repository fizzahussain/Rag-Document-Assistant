import uuid
from pathlib import Path
from tempfile import gettempdir

import anyio
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.core.exceptions import (
    AuthenticationError,
    DatabaseError,
    FileTooLargeError,
    StorageError,
    UnsupportedFileTypeError,
    ValidationError,
)
from backend.app.core.security import (
    get_current_user_id,
    validate_file_extension,
)
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.audio import AudioTranscriptionResponse
from backend.app.schemas.common import ErrorResponse
from backend.app.services.transcription import get_transcription_provider

router = APIRouter(
    prefix="/audio",
    tags=["Audio"],
)


ERROR_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Authentication credentials are missing or invalid",
    },
    status.HTTP_413_CONTENT_TOO_LARGE: {
        "model": ErrorResponse,
        "description": "The uploaded audio exceeds the configured size limit",
    },
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {
        "model": ErrorResponse,
        "description": "The uploaded audio type is not supported",
    },
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErrorResponse,
        "description": "The uploaded audio is invalid or contains no speech",
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "model": ErrorResponse,
        "description": "The transcription service is unavailable",
    },
}


def maximum_audio_size_bytes() -> int:
    """Return the maximum configured audio size in bytes"""

    return int(settings.MAX_AUDIO_SIZE_MB) * 1024 * 1024


async def get_active_user(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> User:
    """Return the authenticated active user"""

    try:
        result = await db.execute(
            select(User).where(
                User.id == user_id,
            )
        )
    except SQLAlchemyError as exc:
        raise DatabaseError(
            message="The user account could not be verified",
        ) from exc

    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError(
            message="User account no longer exists",
        )

    if hasattr(user, "is_active") and not user.is_active:
        raise AuthenticationError(
            message="This user account is disabled",
        )

    return user


async def delete_temporary_audio(path: Path) -> None:
    """Delete a temporary audio file without hiding another error"""

    try:
        temporary_path = anyio.Path(path)

        if await temporary_path.exists():
            await temporary_path.unlink()
    except OSError:
        return


async def save_temporary_audio(
    file: UploadFile,
    extension: str,
) -> Path:
    """Stream an uploaded audio file into temporary storage"""

    temporary_path = Path(gettempdir()) / (f"rag-audio-{uuid.uuid4().hex}.{extension}")
    maximum_size = maximum_audio_size_bytes()
    block_size = int(settings.UPLOAD_BLOCK_SIZE_BYTES)
    total_size = 0

    try:
        async with await anyio.open_file(
            temporary_path,
            mode="wb",
        ) as output:
            while chunk := await file.read(block_size):
                total_size += len(chunk)

                if total_size > maximum_size:
                    raise FileTooLargeError(
                        message=(
                            "The uploaded audio exceeds the "
                            f"{settings.MAX_AUDIO_SIZE_MB} MB size limit"
                        ),
                        details={
                            "maximum_size_mb": settings.MAX_AUDIO_SIZE_MB,
                            "actual_size_bytes": total_size,
                        },
                    )

                await output.write(chunk)
    except FileTooLargeError:
        await delete_temporary_audio(temporary_path)
        raise
    except OSError as exc:
        await delete_temporary_audio(temporary_path)

        raise StorageError(
            message="The uploaded audio could not be stored temporarily",
        ) from exc

    if total_size == 0:
        await delete_temporary_audio(temporary_path)

        raise ValidationError(
            message="The uploaded audio file is empty",
            details={
                "field": "file",
            },
        )

    return temporary_path


@router.post(
    "/transcribe",
    response_model=AudioTranscriptionResponse,
    summary="Transcribe audio",
    description=(
        "Upload an audio recording and convert its speech into text "
        "using the configured local transcription provider."
    ),
    responses=ERROR_RESPONSES,
)
async def transcribe_audio(
    file: UploadFile = File(
        ...,
        description="Audio recording to transcribe",
    ),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> AudioTranscriptionResponse:
    """Transcribe an authenticated user's audio recording"""

    original_filename = file.filename or ""

    if not original_filename.strip():
        await file.close()

        raise ValidationError(
            message="The uploaded audio must have a filename",
            details={
                "field": "file",
            },
        )

    try:
        extension = validate_file_extension(
            original_filename,
            list(settings.ALLOWED_AUDIO_EXTENSIONS),
        )
    except ValidationError as exc:
        await file.close()

        raise UnsupportedFileTypeError(
            message=exc.message,
            details=exc.details,
        ) from exc

    await get_active_user(
        db=db,
        user_id=current_user_id,
    )

    temporary_path: Path | None = None

    try:
        temporary_path = await save_temporary_audio(
            file=file,
            extension=extension,
        )

        provider = get_transcription_provider()
        result = await provider.transcribe(temporary_path)

        return AudioTranscriptionResponse(
            text=result.text,
            language=result.language,
            language_probability=result.language_probability,
            duration_seconds=result.duration_seconds,
            execution_time_seconds=result.execution_time_seconds,
        )
    finally:
        await file.close()

        if temporary_path is not None:
            await delete_temporary_audio(temporary_path)
