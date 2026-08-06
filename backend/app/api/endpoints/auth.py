import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
)
from backend.app.core.security import (
    create_access_token,
    get_current_user_id,
    hash_password,
    verify_password,
)
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from backend.app.schemas.common import ErrorResponse

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


def build_token_response(user: User) -> TokenResponse:
    """Build an authentication response for a user"""

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_TTL_SECONDS,
        user=UserResponse.model_validate(user),
    )


async def find_user_by_email(
    db: AsyncSession,
    email: str,
) -> User | None:
    """Retrieve a user by normalized email address"""

    result = await db.execute(
        select(User).where(
            func.lower(User.email) == email.lower(),
        )
    )

    return result.scalar_one_or_none()


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
    description=(
        "Create a user account and return a bearer access token for authenticated API requests."
    ),
    responses={
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "An account with this email already exists",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "The signup payload is invalid",
        },
    },
)
async def signup(
    request: SignupRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a user and return an access token"""

    email = str(request.email).strip().lower()

    existing_user = await find_user_by_email(
        db=db,
        email=email,
    )

    if existing_user is not None:
        raise ConflictError(
            message="An account with this email already exists",
            details={"field": "email"},
        )

    user = User(
        name=request.name,
        email=email,
        password_hash=hash_password(request.password),
    )

    db.add(user)

    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError as exc:
        await db.rollback()

        raise ConflictError(
            message="An account with this email already exists",
            details={"field": "email"},
        ) from exc
    except Exception:
        await db.rollback()
        raise

    return build_token_response(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Sign in",
    description=(
        "Authenticate with an email address and password and return a bearer access token."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "The email address or password is incorrect",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "The login payload is invalid",
        },
    },
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and return an access token"""

    email = str(request.email).strip().lower()

    user = await find_user_by_email(
        db=db,
        email=email,
    )

    credentials_are_valid = (
        user is not None
        and bool(user.password_hash)
        and verify_password(
            request.password,
            user.password_hash or "",
        )
    )

    if not credentials_are_valid or user is None:
        raise AuthenticationError(
            message="Incorrect email or password",
        )

    if hasattr(user, "is_active") and not user.is_active:
        raise AuthenticationError(
            message="This user account is disabled",
        )

    return build_token_response(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current user",
    description=("Return the profile associated with the supplied bearer access token."),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Authentication credentials are missing or invalid",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "The authenticated user no longer exists",
        },
    },
)
async def get_current_user(
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Return the authenticated user's profile"""

    result = await db.execute(
        select(User).where(
            User.id == current_user_id,
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise NotFoundError(
            message="User account no longer exists",
        )

    if hasattr(user, "is_active") and not user.is_active:
        raise AuthenticationError(
            message="This user account is disabled",
        )

    return UserResponse.model_validate(user)
