import uuid
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.organization import Organization
from app.models.user import User

# OAuth2 scheme that looks for "Authorization: Bearer <token>" header
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency that decodes the access JWT, verifies claims,
    and returns the authenticated active User object with eager-loaded Organization.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        org_id_str = payload.get("org_id")

        if not user_id_str or not org_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_uuid = uuid.UUID(user_id_str)
        org_uuid = uuid.UUID(org_id_str)

    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Query database for user and eagerly load organization
    user = await db.scalar(
        select(User)
        .options(joinedload(User.organization))
        .where(User.id == user_uuid)
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # TENANT ISOLATION DEFENSE: Verify token org_id matches database org_id
    if user.organization_id != org_uuid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Organization tenant mismatch",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_organization(
    current_user: User = Depends(get_current_user),
) -> Organization:
    """
    FastAPI dependency that returns the Organization belonging to the current_user.
    Guarantees strict tenant isolation.
    """
    if not current_user.organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return current_user.organization
