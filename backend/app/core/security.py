import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import bcrypt
import jwt

from app.core.config import settings

JWT_ALGORITHM = "HS256"
TOKEN_TYPE_ACCESS = "access"


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with auto-generated salt."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt hash in constant time."""
    try:
        plain_bytes = plain_password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hash_bytes)
    except Exception:
        return False


def create_access_token(
    user_id: uuid.UUID | str,
    organization_id: uuid.UUID | str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed HS256 access JWT containing sub, org_id, type, iat, exp claims."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "org_id": str(organization_id),
        "type": TOKEN_TYPE_ACCESS,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and verify an HS256 access JWT."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "org_id", "type", "exp", "iat"]},
        )

        if payload.get("type") != TOKEN_TYPE_ACCESS:
            raise ValueError("Invalid token type: expected access token")

        return payload

    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.PyJWTError as e:
        raise ValueError(f"Invalid token: {str(e)}")


def generate_opaque_refresh_token() -> str:
    """Generate a high-entropy, cryptographically secure opaque refresh token."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(raw_token: str) -> str:
    """Compute the 64-character hexadecimal SHA-256 hash of a raw refresh token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
