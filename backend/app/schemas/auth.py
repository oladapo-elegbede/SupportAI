import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    company_name: str = Field(..., min_length=1, max_length=100, description="Company name")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Strips whitespace and lowercases email address."""
        if isinstance(v, str):
            return v.strip().lower()
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Strips whitespace and lowercases email address."""
        if isinstance(v, str):
            return v.strip().lower()
        return v


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """
    Safe user representation for API responses.
    EXCLUDES password_hash to prevent credential leakage.
    """
    id: uuid.UUID
    organization_id: uuid.UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthUserResponse(UserResponse):
    """
    User response extending UserResponse with nested organization details.
    """
    organization: Optional[OrganizationResponse] = None


class TokenResponse(BaseModel):
    """
    Response schema for access token delivery to frontend.
    """
    access_token: str
    token_type: str = "bearer"
