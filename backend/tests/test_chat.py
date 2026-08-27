import io
import time
import uuid
import pytest
import httpx
from sqlalchemy import select, delete

from tests.conftest import TestAsyncSessionLocal
from app.models.organization import Organization
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.llm import PromptBuilder
from app.services.retrieval import RetrievedChunk
from app.services.storage import LocalFileStorage


async def clean_chat_data(email: str, slug: str):
    """Helper to clean up test orgs, users, KBs, and chat conversations."""
    async with TestAsyncSessionLocal() as session:
        org = await session.scalar(select(Organization).where(Organization.slug == slug))
        if org:
            storage = LocalFileStorage("./uploads")
            await storage.delete_directory(str(org.id))
            await session.execute(delete(Organization).where(Organization.id == org.id))
            await session.commit()
        await session.close()


# ============================================================================
# 1. PROMPT BUILDER UNIT TESTS
# ============================================================================

def test_prompt_builder_structure_and_citations():
    sample_chunk = RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename="terms.pdf",
        page_number=1,
        chunk_index=0,
        text="SupportAI terms of service require valid account registration.",
        similarity_score=0.82,
    )

    sys_prompt, user_prompt = PromptBuilder.build_rag_prompt(
        company_name="PyTest Corp",
        query="What are the account registration requirements?",
        retrieved_chunks=[sample_chunk],
    )

    assert "PyTest Corp" in sys_prompt
    assert "<reference_material>" in user_prompt
    assert "terms.pdf" in user_prompt
    assert "Page 1" in user_prompt


# ============================================================================
# 2. ADMIN AUTHENTICATED RAG CHAT INTEGRATION TEST
# ============================================================================

@pytest.mark.asyncio
async def test_admin_rag_chat_flow(client: httpx.AsyncClient):
    email = "chat.admin@pytestcorp.com"
    password = "ChatPassword123!"
    slug = "chat-admin-corp"

    await clean_chat_data(email, slug)

    # Register & Login
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "company_name": "Chat Admin Corp"
    })
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # Create KB & Upload Document
    kb_res = await client.post("/api/v1/knowledge-bases", headers=headers, json={"name": "Warranty KB"})
    kb_id = kb_res.json()["id"]

    files = {"file": ("warranty.txt", io.BytesIO(b"Acme Hardware includes a 2-year warranty on all products."), "text/plain")}
    upload_res = await client.post(f"/api/v1/knowledge-bases/{kb_id}/documents", headers=headers, files=files)
    doc_id = upload_res.json()["id"]

    # Wait for ARQ worker ingestion to complete
    for _ in range(15):
        await asyncio.sleep(1)
        doc_stat = (await client.get(f"/api/v1/documents/{doc_id}", headers=headers)).json()["ingestion_status"]
        if doc_stat == "completed":
            break

    # Admin Chat Request -> 200 OK
    chat_res = await client.post(f"/api/v1/knowledge-bases/{kb_id}/chat", headers=headers, json={
        "message": "What is the warranty period for hardware?"
    })
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert "2-year" in data["message"]["content"]
    assert len(data["sources"]) >= 1
    assert data["sources"][0]["document_name"] == "warranty.txt"

    # List Conversations -> 200 OK
    convos_res = await client.get("/api/v1/conversations", headers=headers)
    assert convos_res.status_code == 200
    assert len(convos_res.json()) == 1

    await clean_chat_data(email, slug)


# ============================================================================
# 3. PUBLIC CUSTOMER-FACING CHAT INTEGRATION TEST (UNAUTHENTICATED)
# ============================================================================

@pytest.mark.asyncio
async def test_public_customer_chat_flow(client: httpx.AsyncClient):
    email = "public.admin@pytestcorp.com"
    password = "PublicPassword123!"
    slug = "public-admin-corp"

    await clean_chat_data(email, slug)

    # Admin registers and sets up KB
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "company_name": "Public Admin Corp"
    })
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    admin_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    kb_res = await client.post("/api/v1/knowledge-bases", headers=admin_headers, json={"name": "Public Widget KB"})
    kb_id = kb_res.json()["id"]

    files = {"file": ("hours.txt", io.BytesIO(b"Support hours are Monday to Friday from 9 AM to 5 PM EST."), "text/plain")}
    upload_res = await client.post(f"/api/v1/knowledge-bases/{kb_id}/documents", headers=admin_headers, files=files)
    doc_id = upload_res.json()["id"]

    for _ in range(15):
        await asyncio.sleep(1)
        if (await client.get(f"/api/v1/documents/{doc_id}", headers=admin_headers)).json()["ingestion_status"] == "completed":
            break

    # Public Chat Request (NO HEADERS!) -> 200 OK
    public_res = await client.post(f"/api/v1/public/chat/{kb_id}", json={
        "message": "What are customer support hours?"
    })
    assert public_res.status_code == 200
    pub_data = public_res.json()
    assert "9 AM to 5 PM" in pub_data["message"]["content"]
    assert pub_data["sources"][0]["document_name"] == "hours.txt"

    await clean_chat_data(email, slug)
