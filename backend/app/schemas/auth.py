import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class SignupRequest(BaseModel):
    """Account registration payload"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "name": "Fizzah Hussain",
                "email": "fizzah@example.com",
                "password": "strong-password-123",
            }
        },
    )

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Display name for the user account",
        examples=["Fizzah Hussain"],
    )
    email: EmailStr = Field(
        ...,
        description="Unique email address used for authentication",
        examples=["fizzah@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Account password",
        examples=["strong-password-123"],
    )

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        """Normalize whitespace in the display name"""

        normalized = " ".join(value.split())

        if len(normalized) < 2:
            raise ValueError("Name must contain at least 2 characters")

        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        """Normalize email addresses before database storage"""

        return str(value).strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """Reject passwords that are too weak"""

        if value != value.strip():
            raise ValueError("Password must not begin or end with whitespace")

        if not any(character.isalpha() for character in value):
            raise ValueError("Password must contain at least one letter")

        if not any(character.isdigit() for character in value):
            raise ValueError("Password must contain at least one number")

        return value


class LoginRequest(BaseModel):
    """Account login payload"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "email": "fizzah@example.com",
                "password": "strong-password-123",
            }
        },
    )

    email: EmailStr = Field(
        ...,
        description="Email address associated with the account",
        examples=["fizzah@example.com"],
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Account password",
        examples=["strong-password-123"],
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        """Normalize the login email address"""

        return str(value).strip().lower()


class UserResponse(BaseModel):
    """Safe public representation of a user account"""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "79cc1183-8fb2-45c8-bf66-41840b520c4c",
                "name": "Fizzah Hussain",
                "email": "fizzah@example.com",
                "is_active": True,
                "created_at": "2026-08-06T10:00:00Z",
                "updated_at": "2026-08-06T10:00:00Z",
            }
        },
    )

    id: uuid.UUID = Field(
        ...,
        description="Unique identifier for the user",
    )
    name: str | None = Field(
        default=None,
        description="Display name for the user",
        examples=["Fizzah Hussain"],
    )
    email: str | None = Field(
        default=None,
        description="Email address associated with the account",
        examples=["fizzah@example.com"],
    )
    is_active: bool = Field(
        default=True,
        description="Whether the user account can authenticate",
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the account was created",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Timestamp when the account was last updated",
    )


class TokenResponse(BaseModel):
    """Bearer token returned after successful authentication"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "encoded-token.signature",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": "79cc1183-8fb2-45c8-bf66-41840b520c4c",
                    "name": "Fizzah Hussain",
                    "email": "fizzah@example.com",
                    "is_active": True,
                    "created_at": "2026-08-06T10:00:00Z",
                    "updated_at": "2026-08-06T10:00:00Z",
                },
            }
        }
    )

    access_token: str = Field(
        ...,
        min_length=1,
        description="Signed bearer token used for authenticated requests",
    )
    token_type: str = Field(
        default="bearer",
        pattern="^bearer$",
        description="Authentication scheme used by the token",
    )
    expires_in: int = Field(
        ...,
        gt=0,
        description="Number of seconds until the token expires",
        examples=[3600],
    )
    user: UserResponse


class CurrentUserResponse(UserResponse):
    """Authenticated user profile response"""


AuthResponse = TokenResponse
