import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_opaque_refresh_token,
    hash_refresh_token,
)
from app.models.organization import Organization
from app.models.user import User
from app.models.refresh_token import RefreshToken


class AuthError(Exception):
    """Base exception for authentication and registration errors."""
    pass


class InvalidCredentialsError(AuthError):
    """Raised when authentication fails due to bad email, bad password, or inactive user."""
    pass


class InvalidTokenError(AuthError):
    """Raised when refresh token validation, rotation, or reuse check fails."""
    pass


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_slug(self, name: str) -> str:
        """Converts 'Acme Corp!' to 'acme-corp'."""
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        return slug if slug else "org"

    async def register_organization_and_owner(self, req) -> User:
        """Atomically registers a new Organization and its initial Owner User."""
        existing_user = await self.db.scalar(
            select(User).where(User.email == req.email)
        )
        if existing_user:
            raise AuthError("Email is already registered.")

        base_slug = self._generate_slug(req.company_name)
        slug = base_slug
        counter = 1
        while await self.db.scalar(select(Organization).where(Organization.slug == slug)):
            slug = f"{base_slug}-{counter}"
            counter += 1

        org = Organization(name=req.company_name, slug=slug)
        self.db.add(org)
        await self.db.flush()

        user = User(
            organization_id=org.id,
            email=req.email,
            password_hash=hash_password(req.password),
            role="owner",
            is_active=True,
        )
        self.db.add(user)

        await self.db.commit()

        user = await self.db.scalar(
            select(User).options(joinedload(User.organization)).where(User.id == user.id)
        )
        return user

    async def authenticate_user(self, email: str, password: str) -> User:
        """Verifies credentials and active status."""
        user = await self.db.scalar(
            select(User).options(joinedload(User.organization)).where(User.email == email.lower())
        )

        if not user:
            raise InvalidCredentialsError("Invalid email or password")
        if not user.is_active:
            raise InvalidCredentialsError("User account is inactive")
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")

        return user

    async def create_session(self, user: User) -> Tuple[str, str]:
        """Creates a new authentication session."""
        access_token = create_access_token(user_id=user.id, organization_id=user.organization_id)

        raw_refresh_token = generate_opaque_refresh_token()
        token_hash = hash_refresh_token(raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        rt_record = RefreshToken(
            user_id=user.id,
            family_id=uuid.uuid4(),
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(rt_record)
        await self.db.commit()

        return access_token, raw_refresh_token

    async def refresh_session(self, raw_refresh_token: str) -> Tuple[str, str]:
        """Validates refresh token, rotates session tokens, with 5-sec grace period for rotation race conditions."""
        token_hash = hash_refresh_token(raw_refresh_token)

        rt_record = await self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )

        if not rt_record:
            raise InvalidTokenError("Invalid refresh token")

        now = datetime.now(timezone.utc)

        # REUSE / THEFT DETECTION WITH 5-SECOND CONCURRENCY GRACE PERIOD FOR ROTATION
        if rt_record.is_revoked:
            if rt_record.revoked_at and (now - rt_record.revoked_at).total_seconds() < 5.0:
                user = await self.db.scalar(select(User).where(User.id == rt_record.user_id))
                if user and user.is_active:
                    access_token = create_access_token(user_id=user.id, organization_id=user.organization_id)
                    new_raw_refresh = generate_opaque_refresh_token()
                    new_token_hash = hash_refresh_token(new_raw_refresh)
                    new_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

                    new_rt_record = RefreshToken(
                        user_id=user.id,
                        family_id=rt_record.family_id,
                        token_hash=new_token_hash,
                        expires_at=new_expires_at,
                    )
                    self.db.add(new_rt_record)
                    await self.db.commit()
                    return access_token, new_raw_refresh

            # Genuine Theft Detected! Revoke entire family.
            await self.db.execute(
                update(RefreshToken)
                .where(RefreshToken.family_id == rt_record.family_id)
                .values(is_revoked=True, revoked_at=now)
            )
            await self.db.commit()
            raise InvalidTokenError("Token reuse detected. Entire session family terminated.")

        # Expiration Check
        if rt_record.expires_at < now:
            rt_record.is_revoked = True
            rt_record.revoked_at = now
            await self.db.commit()
            raise InvalidTokenError("Refresh token expired")

        # Fetch User
        user = await self.db.scalar(select(User).where(User.id == rt_record.user_id))
        if not user or not user.is_active:
            raise InvalidTokenError("User not found or inactive")

        # Rotate Tokens
        rt_record.is_revoked = True
        rt_record.revoked_at = now
        rt_record.last_used_at = now

        access_token = create_access_token(user_id=user.id, organization_id=user.organization_id)

        new_raw_refresh = generate_opaque_refresh_token()
        new_token_hash = hash_refresh_token(new_raw_refresh)
        new_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        new_rt_record = RefreshToken(
            user_id=user.id,
            family_id=rt_record.family_id,
            token_hash=new_token_hash,
            expires_at=new_expires_at,
        )
        self.db.add(new_rt_record)
        await self.db.commit()

        return access_token, new_raw_refresh

    async def logout(self, raw_refresh_token: str) -> None:
        """Revokes session refresh token upon logout (bypasses grace period)."""
        token_hash = hash_refresh_token(raw_refresh_token)
        rt_record = await self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        if rt_record and not rt_record.is_revoked:
            rt_record.is_revoked = True
            # Set revoked_at to 10s in the past so explicit logout skips rotation grace period
            rt_record.revoked_at = datetime.now(timezone.utc) - timedelta(seconds=10)
            await self.db.commit()
