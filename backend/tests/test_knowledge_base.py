import io
import asyncio
import uuid
import pytest
import httpx
from sqlalchemy import select, delete

from tests.conftest import TestAsyncSessionLocal
from app.models.organization import Organization
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.services.storage import LocalFileStorage


async def clean_tenant_data(email: str, slug: str):
    async with TestAsyncSessionLocal() as session:
        org = await session.scalar(select(Organization).where(Organization.slug == slug))
        if org:
            storage = LocalFileStorage("./uploads")
            await storage.delete_directory(str(org.id))
            await session.execute(delete(Organization).where(Organization.id == org.id))
            await session.commit()
        await session.close()


@pytest.mark.asyncio
async def test_kb_crud_lifecycle(client: httpx.AsyncClient):
    email = "kb.owner@pytestcorp.com"
    slug = "kb-corp"
    await clean_tenant_data(email, slug)

    await client.post("/api/v1/auth/register", json={"email": email, "password": "KbPassword123!", "company_name": "KB Corp"})
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": "KbPassword123!"})
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    create_res = await client.post("/api/v1/knowledge-bases", headers=headers, json={"name": "Refund Policies"})
    assert create_res.status_code == 201

    await clean_tenant_data(email, slug)


@pytest.mark.asyncio
async def test_document_upload_and_validation(client: httpx.AsyncClient):
    email = "doc.owner@pytestcorp.com"
    slug = "doc-corp"
    await clean_tenant_data(email, slug)

    await client.post("/api/v1/auth/register", json={"email": email, "password": "DocPassword123!", "company_name": "Doc Corp"})
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": "DocPassword123!"})
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    kb_res = await client.post("/api/v1/knowledge-bases", headers=headers, json={"name": "Tech Specs"})
    kb_id = kb_res.json()["id"]

    txt_files = {"file": ("guide.txt", io.BytesIO(b"Valid UTF-8 plain text content"), "text/plain")}
    txt_res = await client.post(f"/api/v1/knowledge-bases/{kb_id}/documents", headers=headers, files=txt_files)
    assert txt_res.status_code == 201
    
    # In Phase 4, document uploads return 'pending' instead of 'uploaded' due to ARQ enqueue
    assert txt_res.json()["ingestion_status"] == "pending"

    await clean_tenant_data(email, slug)


@pytest.mark.asyncio
async def test_tenant_isolation_cross_tenant_access_blocked(client: httpx.AsyncClient):
    await clean_tenant_data("tenantA@corp.com", "tenant-a")
    await client.post("/api/v1/auth/register", json={"email": "tenantA@corp.com", "password": "Password123!", "company_name": "Tenant A"})
    loginA = await client.post("/api/v1/auth/login", json={"email": "tenantA@corp.com", "password": "Password123!"})
    headersA = {"Authorization": f"Bearer {loginA.json()['access_token']}"}

    kbA = await client.post("/api/v1/knowledge-bases", headers=headersA, json={"name": "Org A Secret KB"})
    kbA_id = kbA.json()["id"]

    await clean_tenant_data("tenantB@corp.com", "tenant-b")
    await client.post("/api/v1/auth/register", json={"email": "tenantB@corp.com", "password": "Password123!", "company_name": "Tenant B"})
    loginB = await client.post("/api/v1/auth/login", json={"email": "tenantB@corp.com", "password": "Password123!"})
    headersB = {"Authorization": f"Bearer {loginB.json()['access_token']}"}

    cross_get = await client.get(f"/api/v1/knowledge-bases/{kbA_id}", headers=headersB)
    assert cross_get.status_code == 404

    await clean_tenant_data("tenantA@corp.com", "tenant-a")
    await clean_tenant_data("tenantB@corp.com", "tenant-b")
