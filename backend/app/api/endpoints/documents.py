import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.core.security import (
    calculate_sha256,
    get_current_user_id,
    validate_file_extension,
    validate_file_size,
)
from backend.app.database import get_db
from backend.app.models.document import Document, DocumentChunk
from backend.app.models.user import User
from backend.app.schemas.document import (
    DocumentChunkResponse,
    DocumentResponse,
    DocumentStatusResponse,
)
from backend.app.services.ingestion import IngestionService
from backend.app.services.storage import StorageService

router = APIRouter(prefix="/documents", tags=["Documents"])


async def get_or_create_user(db: AsyncSession, user_id_str: str) -> User:
    """Helper to retrieve or auto-create a user."""
    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise ValidationError("Invalid user_id format. Must be a valid UUID.")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        user = User(id=user_uuid, workspace_id=str(uuid.uuid4()))
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


@router.post(
    "/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str | None = Form(None),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Uploads, validates, stores, and ingests a document."""
    target_user_id = uuid.UUID(user_id) if user_id else current_user_id
    user = await get_or_create_user(db, str(target_user_id))
    filename = file.filename or "uploaded_file"

    validate_file_extension(filename, settings.ALLOWED_EXTENSIONS)
    file_bytes = await file.read()
    validate_file_size(file_bytes, settings.MAX_UPLOAD_SIZE_MB)

    file_hash = calculate_sha256(file_bytes)
    storage_service = StorageService()
    storage_path = storage_service.save_file(str(user.id), filename, file_bytes)

    # Check for duplicate document for this user
    existing_result = await db.execute(
        select(Document).where(
            Document.user_id == user.id, Document.file_hash == file_hash
        )
    )
    existing_doc = existing_result.scalar_one_or_none()
    if existing_doc:
        existing_doc.status = "queued"
        await db.commit()
        ingestion = IngestionService(db, storage_service)
        return await ingestion.process_document(existing_doc.id)

    # Create new document entry
    doc = Document(
        user_id=user.id,
        filename=filename,
        storage_path=storage_path,
        mime_type=file.content_type or "application/octet-stream",
        file_hash=file_hash,
        file_size=len(file_bytes),
        status="uploaded",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Run ingestion pipeline
    ingestion = IngestionService(db, storage_service)
    processed_doc = await ingestion.process_document(doc.id)
    return processed_doc


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    user_id: str | None = None,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """Lists all uploaded documents for a specific user."""
    target_user_id = uuid.UUID(user_id) if user_id else current_user_id
    user = await get_or_create_user(db, str(target_user_id))
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Retrieves document details by ID."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError(f"Document '{document_id}' not found.")
    return doc


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentStatusResponse:
    """Gets processing status of a document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError(f"Document '{document_id}' not found.")
    return DocumentStatusResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        file_size=doc.file_size,
        updated_at=doc.updated_at,
    )


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkResponse])
async def get_document_chunks(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[DocumentChunkResponse]:
    """Lists extracted text chunks for a document."""
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
    )
    return list(result.scalars().all())


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Reprocesses an existing document idempotently."""
    ingestion = IngestionService(db)
    return await ingestion.process_document(document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    user_id: str | None = None,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deletes document and all related database records and Qdrant points."""
    target_user_id = uuid.UUID(user_id) if user_id else current_user_id
    ingestion = IngestionService(db)
    await ingestion.delete_document(document_id, target_user_id)
