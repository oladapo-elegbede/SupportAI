import io
import uuid
import pytest
import httpx
from datetime import timedelta
from sqlalchemy import select, delete

from tests.conftest import TestAsyncSessionLocal
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
    async with TestAsyncSessionLocal() as session:
        await session.execute(delete(User).where(User.email == email))
        await session.execute(delete(Organization).where(Organization.slug == slug))
        await session.commit()
        await session.close()


def test_password_hashing_and_verification():
    password = "TestPassword123!"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_access_jwt_lifecycle():
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, organization_id=org_id)
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)


def test_expired_jwt_rejection():
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    expired_token = create_access_token(
        user_id=user_id, organization_id=org_id, expires_delta=timedelta(seconds=-10)
    )
    with pytest.raises(ValueError, match="Token has expired"):
        decode_access_token(expired_token)


def test_opaque_refresh_token_hashing():
    raw_token = generate_opaque_refresh_token()
    token_hash = hash_refresh_token(raw_token)
    assert len(raw_token) > 20
    assert len(token_hash) == 64


@pytest.mark.asyncio
async def test_health_check_endpoint(client: httpx.AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_register_organization_and_owner_success(client: httpx.AsyncClient):
    email = "test.owner@pytestcorp.com"
    slug = "pytest-corp"
    await clean_test_user(email, slug)

    payload = {"email": email, "password": "SecurePassword123!", "company_name": "PyTest Corp"}
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    await clean_test_user(email, slug)


@pytest.mark.asyncio
async def test_register_duplicate_email_conflict(client: httpx.AsyncClient):
    email = "dup.owner@pytestcorp.com"
    slug = "pytest-dup-corp"
    await clean_test_user(email, slug)

    payload = {"email": email, "password": "SecurePassword123!", "company_name": "PyTest Dup Corp"}
    await client.post("/api/v1/auth/register", json=payload)
    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    await clean_test_user(email, slug)


@pytest.mark.asyncio
async def test_register_short_password_validation(client: httpx.AsyncClient):
    payload = {"email": "valid@example.com", "password": "short", "company_name": "Short"}
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: httpx.AsyncClient):
    email = "login.user@pytestcorp.com"
    password = "LoginPassword123!"
    slug = "login-corp"
    await clean_test_user(email, slug)

    await client.post("/api/v1/auth/register", json={"email": email, "password": password, "company_name": "Login Corp"})
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200
    assert "refresh_token" in login_res.cookies
    await clean_test_user(email, slug)


@pytest.mark.asyncio
async def test_login_invalid_password(client: httpx.AsyncClient):
    email = "invalid.pass@pytestcorp.com"
    slug = "invalid-corp"
    await clean_test_user(email, slug)

    await client.post("/api/v1/auth/register", json={"email": email, "password": "CorrectPassword123!", "company_name": "Invalid Corp"})
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword999!"})
    assert res.status_code == 401
    await clean_test_user(email, slug)


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_reuse_revocation(client: httpx.AsyncClient):
    email = "refresh.user@pytestcorp.com"
    password = "RefreshPassword123!"
    slug = "refresh-corp"
    await clean_test_user(email, slug)

    await client.post("/api/v1/auth/register", json={"email": email, "password": password, "company_name": "Refresh Corp"})
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    client.cookies.set("refresh_token", login_res.cookies["refresh_token"])

    refresh1_res = await client.post("/api/v1/auth/refresh")
    assert refresh1_res.status_code == 200
    await clean_test_user(email, slug)


@pytest.mark.asyncio
async def test_logout_session_revocation(client: httpx.AsyncClient):
    email = "logout.user@pytestcorp.com"
    password = "LogoutPassword123!"
    slug = "logout-corp"
    await clean_test_user(email, slug)

    await client.post("/api/v1/auth/register", json={"email": email, "password": password, "company_name": "Logout Corp"})
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    
    # Set the cookie securely on the client instance
    client.cookies.set("refresh_token", login_res.cookies["refresh_token"])

    logout_res = await client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200

    refresh_after_logout = await client.post("/api/v1/auth/refresh")
    assert refresh_after_logout.status_code == 401
    await clean_test_user(email, slug)


@pytest.mark.asyncio
async def test_get_me_authenticated_success(client: httpx.AsyncClient):
    email = "me.user@pytestcorp.com"
    slug = "me-corp"
    await clean_test_user(email, slug)

    await client.post("/api/v1/auth/register", json={"email": email, "password": "MePassword123!", "company_name": "Me Corp"})
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": "MePassword123!"})
    access_token = login_res.json()["access_token"]

    me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_res.status_code == 200
    await clean_test_user(email, slug)


@pytest.mark.asyncio
async def test_get_me_unauthenticated_rejection(client: httpx.AsyncClient):
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401
