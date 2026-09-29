"""Pydantic models for the User resource."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Input model for creating a user."""

    email: EmailStr = Field(..., description="User's unique email address")
    full_name: str = Field(..., min_length=1, max_length=255)


class UserResponse(BaseModel):
    """Output model returned to clients."""

    # Allows building the model directly from an asyncpg Record / mapping.
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    created_at: datetime
