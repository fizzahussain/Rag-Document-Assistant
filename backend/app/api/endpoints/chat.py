import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import (
    AuthenticationError,
    DatabaseError,
    NotFoundError,
    ServiceUnavailableError,
)
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
from backend.app.schemas.common import ErrorResponse
from backend.app.services.llm import LLMProviderFactory
from backend.app.services.retrieval import RetrievalService

router = APIRouter(
    tags=["Chat"],
)


COMMON_ERROR_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Authentication credentials are missing or invalid",
    },
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": "The requested conversation or user was not found",
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "model": ErrorResponse,
        "description": "A required database or AI service is unavailable",
    },
}


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
            message="The user account could not be loaded",
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


async def get_owned_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Conversation:
    """Return a conversation owned by the authenticated user"""

    try:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
    except SQLAlchemyError as exc:
        raise DatabaseError(
            message="The conversation could not be loaded",
        ) from exc

    conversation = result.scalar_one_or_none()

    if conversation is None:
        raise NotFoundError(
            message="Conversation not found",
        )

    return conversation


async def create_user_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    title: str,
) -> Conversation:
    """Create and persist a conversation"""

    conversation = Conversation(
        user_id=user_id,
        title=title,
    )

    db.add(conversation)

    try:
        await db.commit()
        await db.refresh(conversation)
    except SQLAlchemyError as exc:
        await db.rollback()

        raise DatabaseError(
            message="The conversation could not be created",
        ) from exc

    return conversation


def build_conversation_title(message: str) -> str:
    """Build a concise title from the first user message"""

    normalized = " ".join(message.split())

    if len(normalized) <= 40:
        return normalized

    return f"{normalized[:37].rstrip()}..."


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask a grounded question",
    description=(
        "Retrieve relevant document chunks, generate a grounded answer, "
        "and store the user and assistant messages."
    ),
    responses={
        **COMMON_ERROR_RESPONSES,
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "The chat request is invalid",
        },
    },
)
async def chat(
    request: ChatRequest,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Generate and store a grounded assistant response"""

    user = await get_active_user(
        db=db,
        user_id=current_user_id,
    )

    if request.conversation_id is not None:
        conversation = await get_owned_conversation(
            db=db,
            conversation_id=request.conversation_id,
            user_id=current_user_id,
        )
    else:
        conversation = await create_user_conversation(
            db=db,
            user_id=user.id,
            title=build_conversation_title(request.message),
        )

    try:
        sources = await RetrievalService(db).search(
            query=request.message,
            user_id=current_user_id,
            limit=request.top_k,
            document_ids=request.document_ids,
        )
    except Exception as exc:
        raise ServiceUnavailableError(
            message="Relevant document content could not be retrieved",
            details={
                "service": "retrieval",
            },
        ) from exc

    try:
        provider = LLMProviderFactory.get_provider()

        rag_result = await provider.generate_answer(
            query=request.message,
            sources=sources,
        )
    except Exception as exc:
        raise ServiceUnavailableError(
            message="The language model could not generate an answer",
            details={
                "service": "llm",
            },
        ) from exc

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=rag_result.answer,
        retrieved_sources={"sources": [source.model_dump(mode="json") for source in sources]},
    )

    db.add_all(
        [
            user_message,
            assistant_message,
        ]
    )

    try:
        await db.commit()
        await db.refresh(assistant_message)
    except SQLAlchemyError as exc:
        await db.rollback()

        raise DatabaseError(
            message="The conversation messages could not be saved",
        ) from exc

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        answer=rag_result.answer,
        citations=rag_result.citations,
        retrieved_sources=rag_result.retrieved_sources,
        execution_time_seconds=rag_result.execution_time_seconds,
    )


@router.get(
    "/conversations",
    response_model=list[ConversationResponse],
    summary="List conversations",
    description=(
        "Return conversations owned by the authenticated user, ordered from newest to oldest."
    ),
    responses=COMMON_ERROR_RESPONSES,
)
async def list_conversations(
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationResponse]:
    """Return conversations owned by the authenticated user"""

    await get_active_user(
        db=db,
        user_id=current_user_id,
    )

    try:
        result = await db.execute(
            select(Conversation)
            .where(
                Conversation.user_id == current_user_id,
            )
            .order_by(
                Conversation.created_at.desc(),
            )
        )
    except SQLAlchemyError as exc:
        raise DatabaseError(
            message="Conversations could not be loaded",
        ) from exc

    return list(result.scalars().all())


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a conversation",
    description="Create an empty conversation for the authenticated user.",
    responses={
        **COMMON_ERROR_RESPONSES,
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "The conversation request is invalid",
        },
    },
)
async def create_conversation(
    request: ConversationCreateRequest,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Create a conversation"""

    user = await get_active_user(
        db=db,
        user_id=current_user_id,
    )

    return await create_user_conversation(
        db=db,
        user_id=user.id,
        title=request.title,
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="List conversation messages",
    description=("Return all messages in an owned conversation in chronological order."),
    responses=COMMON_ERROR_RESPONSES,
)
async def list_messages(
    conversation_id: uuid.UUID,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[MessageResponse]:
    """Return messages from an owned conversation"""

    await get_owned_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user_id,
    )

    try:
        result = await db.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
            )
            .order_by(
                Message.created_at.asc(),
            )
        )
    except SQLAlchemyError as exc:
        raise DatabaseError(
            message="Conversation messages could not be loaded",
        ) from exc

    return list(result.scalars().all())


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
    description=("Delete an owned conversation and its associated messages."),
    responses=COMMON_ERROR_RESPONSES,
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an owned conversation"""

    conversation = await get_owned_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user_id,
    )

    try:
        await db.delete(conversation)
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()

        raise DatabaseError(
            message="The conversation could not be deleted",
        ) from exc
