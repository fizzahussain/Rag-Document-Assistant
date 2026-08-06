import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundError
from backend.app.core.security import get_current_user_id
from backend.app.database import get_db
from backend.app.models.chat import Conversation, Message
from backend.app.models.user import User
from backend.app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationCreateRequest,
    ConversationResponse,
    MessageResponse,
)
from backend.app.services.llm import LLMProviderFactory
from backend.app.services.retrieval import RetrievalService

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    user_result = await db.execute(select(User).where(User.id == current_user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User account not found")
    if request.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == request.conversation_id,
                Conversation.user_id == current_user_id,
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise NotFoundError("Conversation not found")
    else:
        conversation = Conversation(user_id=user.id, title=request.message[:40])
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    sources = await RetrievalService(db).search(
        query=request.message,
        user_id=current_user_id,
        limit=request.top_k,
        document_ids=request.document_ids,
    )
    rag_result = await LLMProviderFactory.get_provider().generate_answer(
        query=request.message,
        sources=sources,
    )
    db.add(
        Message(
            conversation_id=conversation.id,
            role="user",
            content=request.message,
        )
    )
    assistant = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=rag_result.answer,
        retrieved_sources={"sources": [item.model_dump() for item in sources]},
    )
    db.add(assistant)
    await db.commit()
    await db.refresh(assistant)
    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant.id,
        answer=rag_result.answer,
        citations=rag_result.citations,
        retrieved_sources=rag_result.retrieved_sources,
        execution_time_seconds=rag_result.execution_time_seconds,
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationResponse]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user_id)
        .order_by(Conversation.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    request: ConversationCreateRequest,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    user_result = await db.execute(select(User.id).where(User.id == current_user_id))
    if user_result.scalar_one_or_none() is None:
        raise NotFoundError("User account not found")
    conversation = Conversation(user_id=current_user_id, title=request.title)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
async def list_messages(
    conversation_id: uuid.UUID,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[MessageResponse]:
    conversation_result = await db.execute(
        select(Conversation.id).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user_id,
        )
    )
    if conversation_result.scalar_one_or_none() is None:
        raise NotFoundError("Conversation not found")
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise NotFoundError("Conversation not found")
    await db.delete(conversation)
    await db.commit()
