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
from app.services.llm import PromptBuilder
from app.services.retrieval import RetrievedChunk


async def clean_chat_data(email: str, slug: str):
    async with TestAsyncSessionLocal() as session:
        org = await session.scalar(select(Organization).where(Organization.slug == slug))
        if org:
            storage = LocalFileStorage("./uploads")
            await storage.delete_directory(str(org.id))
            await session.execute(delete(Organization).where(Organization.id == org.id))
            await session.commit()
        await session.close()


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


@pytest.mark.asyncio
async def test_admin_rag_chat_flow(client: httpx.AsyncClient):
    email = "chat.admin@pytestcorp.com"
    slug = "chat-admin-corp"
    await clean_chat_data(email, slug)

    await client.post("/api/v1/auth/register", json={"email": email, "password": "ChatPassword123!", "company_name": "Chat Admin Corp"})
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": "ChatPassword123!"})
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    kb_res = await client.post("/api/v1/knowledge-bases", headers=headers, json={"name": "Warranty KB"})
    kb_id = kb_res.json()["id"]

    files = {"file": ("warranty.txt", io.BytesIO(b"Acme Hardware includes a 2-year warranty on all products."), "text/plain")}
    upload_res = await client.post(f"/api/v1/knowledge-bases/{kb_id}/documents", headers=headers, files=files)
    doc_id = upload_res.json()["id"]

    for _ in range(15):
        await asyncio.sleep(1)
        doc_stat = (await client.get(f"/api/v1/documents/{doc_id}", headers=headers)).json()["ingestion_status"]
        if doc_stat == "completed":
            break

    chat_res = await client.post(f"/api/v1/knowledge-bases/{kb_id}/chat", headers=headers, json={"message": "What is the warranty period for hardware?"})
    assert chat_res.status_code == 200

    await clean_chat_data(email, slug)


@pytest.mark.asyncio
async def test_public_customer_chat_flow(client: httpx.AsyncClient):
    email = "public.admin@pytestcorp.com"
    slug = "public-admin-corp"
    await clean_chat_data(email, slug)

    await client.post("/api/v1/auth/register", json={"email": email, "password": "PublicPassword123!", "company_name": "Public Admin Corp"})
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": "PublicPassword123!"})
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

    public_res = await client.post(f"/api/v1/public/chat/{kb_id}", json={"message": "What are customer support hours?"})
    assert public_res.status_code == 200

    await clean_chat_data(email, slug)
