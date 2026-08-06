import json
import uuid
from pathlib import Path

import anyio
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.core.exceptions import (
    AuthenticationError,
    DatabaseError,
    DuplicateDocumentError,
    FileTooLargeError,
    NotFoundError,
    StorageError,
    UnsupportedFileTypeError,
    ValidationError,
)
from backend.app.core.security import (
    get_current_user_id,
    validate_file_extension,
)
from backend.app.database import get_db
from backend.app.models.document import Document, DocumentChunk
from backend.app.models.user import User
from backend.app.schemas.common import ErrorResponse
from backend.app.schemas.document import (
    DocumentChunkResponse,
    DocumentResponse,
    DocumentStatusResponse,
)
from backend.app.services.ingestion import IngestionService
from backend.app.services.storage import StorageService

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


ERROR_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Authentication credentials are missing or invalid",
    },
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": "The requested document was not found",
    },
    status.HTTP_413_CONTENT_TOO_LARGE: {
        "model": ErrorResponse,
        "description": "The uploaded file exceeds the configured size limit",
    },
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {
        "model": ErrorResponse,
        "description": "The uploaded file type is not supported",
    },
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErrorResponse,
        "description": "The uploaded document is invalid",
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "model": ErrorResponse,
        "description": "A required storage or processing service is unavailable",
    },
}


def maximum_upload_size_bytes() -> int:
    """Return the maximum configured upload size in bytes"""

    return int(settings.MAX_UPLOAD_SIZE_MB) * 1024 * 1024


async def get_active_user(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> User:
    """Return the authenticated active user"""

    result = await db.execute(
        select(User).where(
            User.id == user_id,
        )
    )

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


async def get_owned_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Document:
    """Return a document owned by the authenticated user"""

    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
    )

    document = result.scalar_one_or_none()

    if document is None:
        raise NotFoundError(
            message="Document not found",
        )

    return document


async def validate_detectable_content(
    path: str,
    extension: str,
) -> None:
    """Verify that stored content matches its declared file type"""

    file_path = Path(path)

    try:
        file_data = await anyio.Path(file_path).read_bytes()
    except OSError as exc:
        raise StorageError(
            message="The uploaded file could not be read",
        ) from exc

    if not file_data:
        raise ValidationError(
            message="The uploaded file is empty",
        )

    if extension == "pdf" and not file_data.startswith(b"%PDF-"):
        raise ValidationError(
            message="File content does not match PDF format",
            details={
                "expected_format": "pdf",
            },
        )

    if extension == "docx" and not file_data.startswith(b"PK"):
        raise ValidationError(
            message="File content does not match DOCX format",
            details={
                "expected_format": "docx",
            },
        )

    if extension == "json":
        try:
            json.loads(file_data.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise ValidationError(
                message="JSON documents must use UTF-8 encoding",
                details={
                    "expected_encoding": "utf-8",
                },
            ) from exc
        except json.JSONDecodeError as exc:
            raise ValidationError(
                message="The uploaded JSON document is invalid",
                details={
                    "line": exc.lineno,
                    "column": exc.colno,
                },
            ) from exc


async def safely_delete_stored_file(
    storage: StorageService,
    path: str,
) -> None:
    """Delete a stored file without hiding the original exception"""

    try:
        await storage.delete_file(path)
    except Exception:
        return


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
    description=(
        "Upload, validate, store, extract, chunk, embed, and index a "
        "document for the authenticated user."
    ),
    responses={
        **ERROR_RESPONSES,
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "The same document has already been uploaded",
        },
    },
)
async def upload_document(
    file: UploadFile = File(
        ...,
        description="Document to upload and index",
    ),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Upload and process a document"""

    original_filename = file.filename or ""

    if not original_filename.strip():
        raise ValidationError(
            message="The uploaded file must have a filename",
            details={
                "field": "file",
            },
        )

    try:
        extension = validate_file_extension(
            original_filename,
            list(settings.ALLOWED_EXTENSIONS),
        )
    except ValidationError as exc:
        raise UnsupportedFileTypeError(
            message=exc.message,
            details=exc.details,
        ) from exc

    user = await get_active_user(
        db=db,
        user_id=current_user_id,
    )

    storage = StorageService()

    try:
        stored = await storage.save_upload(
            str(user.id),
            file,
        )
    except ValidationError:
        raise
    except Exception as exc:
        raise StorageError(
            message="The uploaded file could not be stored",
        ) from exc
    finally:
        await file.close()

    maximum_size = maximum_upload_size_bytes()

    if stored.size > maximum_size:
        await safely_delete_stored_file(
            storage=storage,
            path=stored.path,
        )

        raise FileTooLargeError(
            message=(f"The uploaded file exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB size limit"),
            details={
                "maximum_size_mb": settings.MAX_UPLOAD_SIZE_MB,
                "actual_size_bytes": stored.size,
            },
        )

    try:
        await validate_detectable_content(
            path=stored.path,
            extension=extension,
        )
    except Exception:
        await safely_delete_stored_file(
            storage=storage,
            path=stored.path,
        )
        raise

    try:
        existing_result = await db.execute(
            select(Document).where(
                Document.user_id == user.id,
                Document.file_hash == stored.sha256,
            )
        )
    except SQLAlchemyError as exc:
        await safely_delete_stored_file(
            storage=storage,
            path=stored.path,
        )

        raise DatabaseError(
            message="The document could not be checked for duplicates",
        ) from exc

    existing_document = existing_result.scalar_one_or_none()

    if existing_document is not None:
        await safely_delete_stored_file(
            storage=storage,
            path=stored.path,
        )

        raise DuplicateDocumentError(
            details={
                "document_id": str(existing_document.id),
                "filename": existing_document.filename,
            },
        )

    document = Document(
        user_id=user.id,
        filename=stored.original_filename,
        storage_path=stored.path,
        mime_type=file.content_type or "application/octet-stream",
        file_hash=stored.sha256,
        file_size=stored.size,
        status="uploaded",
    )

    db.add(document)

    try:
        await db.commit()
        await db.refresh(document)
    except SQLAlchemyError as exc:
        await db.rollback()

        await safely_delete_stored_file(
            storage=storage,
            path=stored.path,
        )

        raise DatabaseError(
            message="The document record could not be created",
        ) from exc

    ingestion = IngestionService(
        db,
        storage,
    )

    return await ingestion.process_document(
        document.id,
        current_user_id,
    )


@router.get(
    "",
    response_model=list[DocumentResponse],
    summary="List documents",
    description="Return documents owned by the authenticated user.",
    responses={
        status.HTTP_401_UNAUTHORIZED: ERROR_RESPONSES[status.HTTP_401_UNAUTHORIZED],
        status.HTTP_503_SERVICE_UNAVAILABLE: ERROR_RESPONSES[status.HTTP_503_SERVICE_UNAVAILABLE],
    },
)
async def list_documents(
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """List documents belonging to the authenticated user"""

    await get_active_user(
        db=db,
        user_id=current_user_id,
    )

    try:
        result = await db.execute(
            select(Document)
            .where(
                Document.user_id == current_user_id,
            )
            .order_by(
                Document.created_at.desc(),
            )
        )
    except SQLAlchemyError as exc:
        raise DatabaseError(
            message="Documents could not be loaded",
        ) from exc

    return list(result.scalars().all())


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get a document",
    description="Return one document owned by the authenticated user.",
    responses=ERROR_RESPONSES,
)
async def get_document(
    document_id: uuid.UUID,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Return one owned document"""

    return await get_owned_document(
        db=db,
        document_id=document_id,
        user_id=current_user_id,
    )


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Get document status",
    description=("Return the current processing status of an owned document."),
    responses=ERROR_RESPONSES,
)
async def get_document_status(
    document_id: uuid.UUID,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentStatusResponse:
    """Return document processing status"""

    document = await get_owned_document(
        db=db,
        document_id=document_id,
        user_id=current_user_id,
    )

    return DocumentStatusResponse(
        id=document.id,
        filename=document.filename,
        status=document.status,
        file_size=document.file_size,
        updated_at=document.updated_at,
    )


@router.get(
    "/{document_id}/chunks",
    response_model=list[DocumentChunkResponse],
    summary="List document chunks",
    description=("Return extracted chunks for a document owned by the authenticated user."),
    responses=ERROR_RESPONSES,
)
async def get_document_chunks(
    document_id: uuid.UUID,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentChunkResponse]:
    """Return chunks for one owned document"""

    await get_owned_document(
        db=db,
        document_id=document_id,
        user_id=current_user_id,
    )

    try:
        result = await db.execute(
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id,
            )
            .order_by(
                DocumentChunk.chunk_index.asc(),
            )
        )
    except SQLAlchemyError as exc:
        raise DatabaseError(
            message="Document chunks could not be loaded",
        ) from exc

    return list(result.scalars().all())


@router.post(
    "/{document_id}/reprocess",
    response_model=DocumentResponse,
    summary="Reprocess a document",
    description=("Extract, chunk, embed, and index an owned document again."),
    responses={
        **ERROR_RESPONSES,
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "The document cannot currently be reprocessed",
        },
    },
)
async def reprocess_document(
    document_id: uuid.UUID,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Reprocess an owned document"""

    document = await get_owned_document(
        db=db,
        document_id=document_id,
        user_id=current_user_id,
    )

    if document.status in {
        "processing",
        "deleting",
    }:
        raise ValidationError(
            message=(f"Document cannot be reprocessed while its status is '{document.status}'"),
            details={
                "document_id": str(document.id),
                "status": document.status,
            },
        )

    storage = StorageService()
    ingestion = IngestionService(
        db,
        storage,
    )

    return await ingestion.process_document(
        document_id,
        current_user_id,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    description=("Delete an owned document, its stored file, chunks, and vectors."),
    responses=ERROR_RESPONSES,
)
async def delete_document(
    document_id: uuid.UUID,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an owned document and its associated data"""

    document = await get_owned_document(
        db=db,
        document_id=document_id,
        user_id=current_user_id,
    )

    if document.status == "deleting":
        raise ValidationError(
            message="Document deletion is already in progress",
            details={
                "document_id": str(document.id),
            },
        )

    storage = StorageService()
    ingestion = IngestionService(
        db,
        storage,
    )

    await ingestion.delete_document(
        document_id,
        current_user_id,
    )
