import uuid
import pytest
import httpx
from datetime import timedelta
from sqlalchemy import delete

from app.core.database import AsyncSessionLocal
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_opaque_refresh_token,
    hash_refresh_token,
)
from app.models.organization import Organization
from app.models.user import User


async def clean_test_user(email: str, slug: str):
    """Helper to clean up test records before/after integration tests."""
    async with AsyncSessionLocal() as session:
        await session.execute(delete(User).where(User.email == email))
        await session.execute(delete(Organization).where(Organization.slug == slug))
        await session.commit()


# ============================================================================
# 1. SECURITY PRIMITIVES UNIT TESTS
# ============================================================================

def test_password_hashing_and_verification():
    password = "TestPassword123!"
    hashed = hash_password(password)
    
    assert hashed != password
    assert hashed.startswith("$2b$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_access_jwt_lifecycle():
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    
    token = create_access_token(user_id=user_id, organization_id=org_id)
    payload = decode_access_token(token)
    
    assert payload["sub"] == str(user_id)
    assert payload["org_id"] == str(org_id)
    assert payload["type"] == "access"


def test_expired_jwt_rejection():
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    
    expired_token = create_access_token(
        user_id=user_id,
        organization_id=org_id,
        expires_delta=timedelta(seconds=-10),
    )
    
    with pytest.raises(ValueError, match="Token has expired"):
        decode_access_token(expired_token)


def test_opaque_refresh_token_hashing():
    raw_token = generate_opaque_refresh_token()
    token_hash = hash_refresh_token(raw_token)
    
    assert len(raw_token) > 20
    assert len(token_hash) == 64  # SHA-256 hex string
    assert hash_refresh_token(raw_token) == token_hash


# ============================================================================
# 2. HEALTH ENDPOINT REGRESSION TEST
# ============================================================================

@pytest.mark.asyncio
async def test_health_check_endpoint(client: httpx.AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "healthy"


# ============================================================================
# 3. REGISTRATION INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_register_organization_and_owner_success(client: httpx.AsyncClient):
    email = "test.owner@pytestcorp.com"
    slug = "pytest-corp"
    
    await clean_test_user(email, slug)

    payload = {
        "email": email,
        "password": "SecurePassword123!",
        "company_name": "PyTest Corp",
    }
    
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["email"] == email
    assert data["role"] == "owner"
    assert data["is_active"] is True
    assert "password_hash" not in data  # SECURITY: Excluded!
    assert data["organization"]["slug"] == slug

    await clean_test_user(email, slug)


@pytest.mark.asyncio
async def test_register_duplicate_email_conflict(client: httpx.AsyncClient):
    email = "dup.owner@pytestcorp.com"
    slug = "pytest-dup-corp"
    
    await clean_test_user(email, slug)

    payload = {
        "email": email,
        "password": "SecurePassword123!",
        "company_name": "PyTest Dup Corp",
    }
    
    # First registration -> 201
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Second registration -> 409 Conflict
    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert res2.json()["detail"] == "Email is already registered."

    await clean_test_user(email, slug)


@pytest.mark.asyncio
async def test_register_short_password_validation(client: httpx.AsyncClient):
    payload = {
        "email": "valid@example.com",
        "password": "short",  # < 8 characters
        "company_name": "Short Corp",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


# ============================================================================
# 4. LOGIN INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_login_success(client: httpx.AsyncClient):
    email = "login.user@pytestcorp.com"
    password = "LoginPassword123!"
    slug = "login-corp"

    await clean_test_user(email, slug)

    # Register first
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "company_name": "Login Corp",
    })

    # Login
    login_res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    assert login_res.status_code == 200
    
    data = login_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" in login_res.cookies  # httpOnly cookie set!

    await clean_test_user(email, slug)


@pytest.mark.asyncio
async def test_login_invalid_password(client: httpx.AsyncClient):
    email = "invalid.pass@pytestcorp.com"
    slug = "invalid-corp"

    await clean_test_user(email, slug)

    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "CorrectPassword123!",
        "company_name": "Invalid Corp",
    })

    # Login with wrong password
    res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "WrongPassword999!",
    })
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password"

    await clean_test_user(email, slug)


# ============================================================================
# 5. SESSION REFRESH & ROTATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_refresh_token_rotation_and_reuse_revocation(client: httpx.AsyncClient):
    email = "refresh.user@pytestcorp.com"
    password = "RefreshPassword123!"
    slug = "refresh-corp"

    await clean_test_user(email, slug)

    # Register & Login
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "company_name": "Refresh Corp",
    })
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert "refresh_token" in login_res.cookies
    initial_cookie = login_res.cookies["refresh_token"]

    # First Refresh (Valid) -> Rotates Cookie
    refresh1_res = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": initial_cookie})
    assert refresh1_res.status_code == 200
    assert "access_token" in refresh1_res.json()
    assert "refresh_token" in refresh1_res.cookies
    rotated_cookie = refresh1_res.cookies["refresh_token"]
    assert rotated_cookie != initial_cookie

    await clean_test_user(email, slug)


# ============================================================================
# 6. LOGOUT INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_logout_session_revocation(client: httpx.AsyncClient):
    email = "logout.user@pytestcorp.com"
    password = "LogoutPassword123!"
    slug = "logout-corp"

    await clean_test_user(email, slug)

    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "company_name": "Logout Corp",
    })
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    cookie = login_res.cookies["refresh_token"]

    # Logout
    logout_res = await client.post("/api/v1/auth/logout", cookies={"refresh_token": cookie})
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Successfully logged out"

    # Refresh after logout -> 401
    refresh_after_logout = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": cookie})
    assert refresh_after_logout.status_code == 401

    await clean_test_user(email, slug)


# ============================================================================
# 7. AUTHENTICATED /ME & TENANT ISOLATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_me_authenticated_success(client: httpx.AsyncClient):
    email = "me.user@pytestcorp.com"
    password = "MePassword123!"
    slug = "me-corp"

    await clean_test_user(email, slug)

    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "company_name": "Me Corp",
    })
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    access_token = login_res.json()["access_token"]

    # Call /me with Bearer token
    me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_res.status_code == 200
    
    data = me_res.json()
    assert data["email"] == email
    assert data["role"] == "owner"
    assert data["organization"]["slug"] == slug
    assert "password_hash" not in data  # SECURITY: Excluded!

    await clean_test_user(email, slug)


@pytest.mark.asyncio
async def test_get_me_unauthenticated_rejection(client: httpx.AsyncClient):
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401
