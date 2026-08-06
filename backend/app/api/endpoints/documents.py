import json
import uuid

import anyio
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.core.security import get_current_user_id, validate_file_extension
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


async def ensure_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(id=user_id, workspace_id=str(uuid.uuid4()))
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def validate_detectable_content(path: str, extension: str) -> None:
    data = await anyio.Path(path).read_bytes()
    if extension == "pdf" and not data.startswith(b"%PDF-"):
        raise ValidationError("File content does not match PDF format")
    if extension == "docx" and not data.startswith(b"PK"):
        raise ValidationError("File content does not match DOCX format")
    if extension == "json":
        try:
            json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError("Invalid JSON document") from exc


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    extension = validate_file_extension(
        file.filename or "",
        list(settings.ALLOWED_EXTENSIONS),
    )
    user = await ensure_user(db, current_user_id)
    storage = StorageService()
    stored = await storage.save_upload(str(user.id), file)
    try:
        await validate_detectable_content(stored.path, extension)
    except Exception:
        await storage.delete_file(stored.path)
        raise

    existing_result = await db.execute(
        select(Document).where(
            Document.user_id == user.id,
            Document.file_hash == stored.sha256,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        await storage.delete_file(stored.path)
        return existing

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
    await db.commit()
    await db.refresh(document)
    return await IngestionService(db, storage).process_document(
        document.id,
        current_user_id,
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    result = await db.execute(
        select(Document)
        .where(Document.user_id == current_user_id)
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def owned_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Document:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise NotFoundError("Document not found")
    return document


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    return await owned_document(db, document_id, current_user_id)


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: uuid.UUID,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentStatusResponse:
    document = await owned_document(db, document_id, current_user_id)
    return DocumentStatusResponse(
        id=document.id,
        filename=document.filename,
        status=document.status,
        file_size=document.file_size,
        updated_at=document.updated_at,
    )


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkResponse])
async def get_document_chunks(
    document_id: uuid.UUID,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentChunkResponse]:
    await owned_document(db, document_id, current_user_id)
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
    )
    return list(result.scalars().all())


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(
    document_id: uuid.UUID,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    await owned_document(db, document_id, current_user_id)
    return await IngestionService(db).process_document(document_id, current_user_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    await IngestionService(db).delete_document(document_id, current_user_id)
