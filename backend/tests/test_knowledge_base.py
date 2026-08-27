import io
import uuid
import pytest
import httpx
from sqlalchemy import select, delete

from app.core.database import AsyncSessionLocal
from app.models.organization import Organization
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.services.storage import LocalFileStorage


async def clean_tenant_data(email: str, slug: str):
    """Helper to clean up test orgs, users, KBs, and disk files."""
    async with AsyncSessionLocal() as session:
        org = await session.scalar(select(Organization).where(Organization.slug == slug))
        if org:
            # Purge tenant disk files
            storage = LocalFileStorage("./uploads")
            await storage.delete_directory(str(org.id))
            
            await session.execute(delete(Organization).where(Organization.id == org.id))
            await session.commit()
        await session.close()


# ============================================================================
# 1. KNOWLEDGE BASE INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_kb_crud_lifecycle(client: httpx.AsyncClient):
    email = "kb.owner@pytestcorp.com"
    password = "KbPassword123!"
    slug = "kb-corp"

    await clean_tenant_data(email, slug)

    # Register & Login
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "company_name": "KB Corp"
    })
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # 1. Create KB (201)
    create_res = await client.post("/api/v1/knowledge-bases", headers=headers, json={
        "name": "Refund Policies",
        "description": "Customer refund guides"
    })
    assert create_res.status_code == 201
    kb_id = create_res.json()["id"]
    assert create_res.json()["name"] == "Refund Policies"
    assert create_res.json()["document_count"] == 0

    # 2. Duplicate KB Name -> 409 Conflict
    dup_res = await client.post("/api/v1/knowledge-bases", headers=headers, json={
        "name": "Refund Policies"
    })
    assert dup_res.status_code == 409

    # 3. List KBs -> 200
    list_res = await client.get("/api/v1/knowledge-bases", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 4. Update KB -> 200
    update_res = await client.patch(f"/api/v1/knowledge-bases/{kb_id}", headers=headers, json={
        "name": "Updated Refund Policies"
    })
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Updated Refund Policies"

    # 5. Delete KB -> 200
    del_res = await client.delete(f"/api/v1/knowledge-bases/{kb_id}", headers=headers)
    assert del_res.status_code == 200

    await clean_tenant_data(email, slug)


# ============================================================================
# 2. DOCUMENT UPLOAD & VALIDATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_document_upload_and_validation(client: httpx.AsyncClient):
    email = "doc.owner@pytestcorp.com"
    password = "DocPassword123!"
    slug = "doc-corp"

    await clean_tenant_data(email, slug)

    # Register & Login
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "company_name": "Doc Corp"
    })
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # Create KB
    kb_res = await client.post("/api/v1/knowledge-bases", headers=headers, json={"name": "Tech Specs"})
    kb_id = kb_res.json()["id"]

    # 1. Upload Valid TXT Document (201)
    txt_files = {"file": ("guide.txt", io.BytesIO(b"Valid UTF-8 plain text content"), "text/plain")}
    txt_res = await client.post(f"/api/v1/knowledge-bases/{kb_id}/documents", headers=headers, files=txt_files)
    assert txt_res.status_code == 201
    doc1_id = txt_res.json()["id"]
    assert txt_res.json()["file_type"] == "txt"
    assert txt_res.json()["ingestion_status"] == "uploaded"

    # 2. Upload Valid PDF Document with %PDF- Header (201)
    pdf_files = {"file": ("manual.pdf", io.BytesIO(b"%PDF-1.4 Fake PDF Header Content"), "application/pdf")}
    pdf_res = await client.post(f"/api/v1/knowledge-bases/{kb_id}/documents", headers=headers, files=pdf_files)
    assert pdf_res.status_code == 201
    assert pdf_res.json()["file_type"] == "pdf"

    # 3. Invalid Extension -> 400 Bad Request
    exe_files = {"file": ("malware.exe", io.BytesIO(b"executable content"), "application/octet-stream")}
    exe_res = await client.post(f"/api/v1/knowledge-bases/{kb_id}/documents", headers=headers, files=exe_files)
    assert exe_res.status_code == 400
    assert "Only PDF (.pdf) and Plain Text (.txt) files are allowed" in exe_res.json()["detail"]

    # 4. Fake PDF Magic Bytes -> 400 Bad Request
    fake_pdf_files = {"file": ("fake.pdf", io.BytesIO(b"Not a PDF header"), "application/pdf")}
    fake_res = await client.post(f"/api/v1/knowledge-bases/{kb_id}/documents", headers=headers, files=fake_pdf_files)
    assert fake_res.status_code == 400
    assert "Invalid PDF file format" in fake_res.json()["detail"]

    # 5. Delete Document (200)
    del_doc_res = await client.delete(f"/api/v1/documents/{doc1_id}", headers=headers)
    assert del_doc_res.status_code == 200

    await clean_tenant_data(email, slug)


# ============================================================================
# 3. MULTI-TENANT ISOLATION DEFENSE TEST
# ============================================================================

@pytest.mark.asyncio
async def test_tenant_isolation_cross_tenant_access_blocked(client: httpx.AsyncClient):
    # Setup Tenant A
    await clean_tenant_data("tenantA@corp.com", "tenant-a")
    await client.post("/api/v1/auth/register", json={"email": "tenantA@corp.com", "password": "Password123!", "company_name": "Tenant A"})
    loginA = await client.post("/api/v1/auth/login", json={"email": "tenantA@corp.com", "password": "Password123!"})
    headersA = {"Authorization": f"Bearer {loginA.json()['access_token']}"}

    # Tenant A creates KB
    kbA = await client.post("/api/v1/knowledge-bases", headers=headersA, json={"name": "Org A Secret KB"})
    kbA_id = kbA.json()["id"]

    # Setup Tenant B
    await clean_tenant_data("tenantB@corp.com", "tenant-b")
    await client.post("/api/v1/auth/register", json={"email": "tenantB@corp.com", "password": "Password123!", "company_name": "Tenant B"})
    loginB = await client.post("/api/v1/auth/login", json={"email": "tenantB@corp.com", "password": "Password123!"})
    headersB = {"Authorization": f"Bearer {loginB.json()['access_token']}"}

    # ATTACK TEST: Tenant B attempts to access Tenant A's KB -> 404 Not Found
    cross_get = await client.get(f"/api/v1/knowledge-bases/{kbA_id}", headers=headersB)
    assert cross_get.status_code == 404

    # ATTACK TEST: Tenant B attempts to upload to Tenant A's KB -> 404 Not Found
    attack_file = {"file": ("attack.txt", io.BytesIO(b"unauthorized upload"), "text/plain")}
    cross_upload = await client.post(f"/api/v1/knowledge-bases/{kbA_id}/documents", headers=headersB, files=attack_file)
    assert cross_upload.status_code == 404

    # ATTACK TEST: Tenant B attempts to delete Tenant A's KB -> 404 Not Found
    cross_delete = await client.delete(f"/api/v1/knowledge-bases/{kbA_id}", headers=headersB)
    assert cross_delete.status_code == 404

    # Cleanup
    await clean_tenant_data("tenantA@corp.com", "tenant-a")
    await clean_tenant_data("tenantB@corp.com", "tenant-b")
