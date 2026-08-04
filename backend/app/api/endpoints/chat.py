from typing import List
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.database import get_db
from backend.app.models.chat import Conversation, Message
from backend.app.models.user import User
from backend.app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse, MessageResponse
from backend.app.services.llm import LLMProviderFactory
from backend.app.services.retrieval import RetrievalService

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Executes RAG flow: context retrieval -> prompt -> LLM answer generation -> citation tracking."""
    # 1. Ensure user exists
    user_res = await db.execute(select(User).where(User.id == request.user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        user = User(id=request.user_id, workspace_id=str(uuid.uuid4()))
        db.add(user)
        await db.commit()

    # 2. Ensure or create conversation session
    if request.conversation_id:
        conv_res = await db.execute(select(Conversation).where(Conversation.id == request.conversation_id))
        conversation = conv_res.scalar_one_or_none()
        if not conversation:
            raise NotFoundError(f"Conversation '{request.conversation_id}' not found.")
    else:
        conversation = Conversation(user_id=user.id, title=request.message[:40])
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    # 3. Retrieve relevant vector context
    retrieval_service = RetrievalService()
    doc_ids_str = [str(d) for d in request.document_ids] if request.document_ids else None
    
    retrieved_sources = await retrieval_service.search(
        query=request.message,
        user_id=str(user.id),
        limit=request.top_k,
        document_ids=doc_ids_str,
    )

    # 4. Generate answer using LLM
    llm = LLMProviderFactory.get_provider()
    rag_result = await llm.generate_answer(query=request.message, sources=retrieved_sources)

    # 5. Persist user message and assistant message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)

    sources_json = [s.model_dump() for s in retrieved_sources]
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=rag_result.answer,
        retrieved_sources={"sources": sources_json},
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_msg.id,
        answer=rag_result.answer,
        citations=rag_result.citations,
        retrieved_sources=rag_result.retrieved_sources,
        execution_time_seconds=rag_result.execution_time_seconds,
    )


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[ConversationResponse]:
    """Lists all active chat conversations for a user."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise ValidationError("Invalid user_id format.")

    result = await db.execute(
        select(Conversation).where(Conversation.user_id == user_uuid).order_by(Conversation.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    user_id: str,
    title: str = "New Conversation",
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Creates a new conversation session."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise ValidationError("Invalid user_id format.")

    conv = Conversation(user_id=user_uuid, title=title)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def list_messages(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[MessageResponse]:
    """Gets message history for a conversation."""
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deletes a conversation and all history messages."""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise NotFoundError(f"Conversation '{conversation_id}' not found.")
    await db.delete(conv)
    await db.commit()
