import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

import asyncio
import json
import uuid
from typing import Any, Dict, List
import structlog
from sqlalchemy import select, delete

from app.core.database import AsyncSessionLocal
from app.models.organization import Organization
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.schemas.knowledge_base import KnowledgeBaseCreate
from app.schemas.chat import ChatMessageRequest
from app.services.knowledge_base import KBService
from app.services.document import DocumentService
from app.services.ingestion import IngestionService
from app.services.retrieval import RetrievalService
from app.services.chat import ChatService

logger = structlog.get_logger("supportai.eval")


async def run_evaluation():
    print("\n" + "=" * 75)
    print("🚀 SUPPORTAI LOCAL RAG QUALITY EVALUATION BENCHMARK (₦0 COST)")
    print("=" * 75)

    dataset_path = backend_root / "scripts" / "eval_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset: List[Dict[str, Any]] = json.load(f)

    print(f"• Loaded {len(dataset)} Ground-Truth Test Cases from scripts/eval_dataset.json\n")

    async with AsyncSessionLocal() as db:
        slug = "rag-eval-org"
        
        # Cleanup pre-existing test data
        existing_org = await db.scalar(select(Organization).where(Organization.slug == slug))
        if existing_org:
            await db.execute(delete(Organization).where(Organization.id == existing_org.id))
            await db.commit()

        # Provision Test Tenant & KB
        org = Organization(name="RAG Eval Org", slug=slug)
        db.add(org)
        await db.commit()
        org_id = org.id

        kb_service = KBService(db)
        doc_service = DocumentService(db)
        ingestion_service = IngestionService(db)
        retrieval_service = RetrievalService(db, top_k=3, similarity_threshold=0.0)
        chat_service = ChatService(db, retrieval_service=retrieval_service)

        kb = await kb_service.create_kb(org_id, KnowledgeBaseCreate(name="Evaluation KB"))
        kb_id = kb.id

        # 1. Ingest Dataset Documents into pgvector and wait for completion
        print("• Ingesting Evaluation Documents into pgvector...")
        ingested_docs = {}
        for tc in dataset:
            filename = tc["document_filename"]
            if filename and filename not in ingested_docs:
                content = tc["document_content"].encode("utf-8")
                doc = await doc_service.upload_document(org_id, kb_id, filename, content)
                
                # Poll until background ingestion finishes or run directly
                for _ in range(15):
                    await asyncio.sleep(1)
                    await db.refresh(doc)
                    if doc.ingestion_status == "completed":
                        break
                
                if doc.ingestion_status != "completed":
                    await ingestion_service.process_document(doc.id, org_id)

                ingested_docs[filename] = doc.id
                print(f"  ✓ Ingested document: {filename} (Status: {doc.ingestion_status})")

        print("\n" + "-" * 75)
        print(f"{'ID':<8} | {'CATEGORY':<14} | {'HIT@3':<6} | {'RR':<6} | {'KW RECALL':<10} | {'REFUSAL':<8}")
        print("-" * 75)

        total_in_context = 0
        total_out_of_context = 0
        hits = 0
        reciprocal_ranks = []
        keyword_recall_scores = []
        correct_refusals = 0

        for tc in dataset:
            tc_id = tc["id"]
            category = tc["category"]
            query = tc["query"]
            expected_doc = tc["expected_source_document"]
            expected_kws = tc["expected_keywords"]
            is_ooc = tc["is_out_of_context"]

            # Step A: Evaluate Retrieval (Hit@3 & MRR)
            retrieved = await retrieval_service.retrieve_relevant_chunks(org_id, kb_id, query, top_k=3)
            retrieved_files = [c.filename for c in retrieved]

            hit = False
            rr = 0.0
            if expected_doc and expected_doc in retrieved_files:
                hit = True
                rank = retrieved_files.index(expected_doc) + 1
                rr = 1.0 / rank

            if not is_ooc:
                total_in_context += 1
                if hit:
                    hits += 1
                reciprocal_ranks.append(rr)

            # Step B: Evaluate Chat Generation & Refusal
            chat_req = ChatMessageRequest(message=query)
            chat_resp = await chat_service.send_message(org_id, kb_id, chat_req)
            ai_answer = chat_resp.message.content.lower()

            kw_recall_str = "N/A"
            refusal_str = "N/A"

            if not is_ooc:
                # Check Keyword Coverage
                found_kws = sum(1 for kw in expected_kws if kw.lower() in ai_answer)
                kw_recall = (found_kws / len(expected_kws)) * 100 if expected_kws else 100.0
                keyword_recall_scores.append(kw_recall)
                kw_recall_str = f"{kw_recall:.0f}%"
            else:
                total_out_of_context += 1
                # Check Grounded Refusal
                is_refused = ("don't have enough information" in ai_answer or "sorry" in ai_answer or "cannot answer" in ai_answer)
                if is_refused:
                    correct_refusals += 1
                    refusal_str = "PASS"
                else:
                    refusal_str = "FAIL"

            hit_str = "PASS" if hit else ("N/A" if is_ooc else "FAIL")
            rr_str = f"{rr:.2f}" if not is_ooc else "N/A"

            print(f"{tc_id:<8} | {category:<14} | {hit_str:<6} | {rr_str:<6} | {kw_recall_str:<10} | {refusal_str:<8}")

        # Summary Metrics
        hit_rate = (hits / total_in_context * 100) if total_in_context else 0.0
        mrr = (sum(reciprocal_ranks) / total_in_context) if total_in_context else 0.0
        avg_kw_recall = (sum(keyword_recall_scores) / len(keyword_recall_scores)) if keyword_recall_scores else 0.0
        refusal_rate = (correct_refusals / total_out_of_context * 100) if total_out_of_context else 0.0

        print("=" * 75)
        print("AGGREGATE RAG QUALITY BENCHMARK RESULTS")
        print("=" * 75)
        print(f"• Context Retrieval Hit Rate (Hit@3):  {hit_rate:.1f}%  (Target: >= 90%)")
        print(f"• Mean Reciprocal Rank (MRR):          {mrr:.2f}   (Target: >= 0.85)")
        print(f"• Answer Keyword Recall:              {avg_kw_recall:.1f}%  (Target: >= 80%)")
        print(f"• Refusal Guardrail Correctness:      {refusal_rate:.1f}%  (Target: 100%)")
        print("=" * 75 + "\n")

        # Cleanup
        await kb_service.delete_kb(org_id, kb_id)
        await db.execute(delete(Organization).where(Organization.id == org_id))
        await db.commit()
        print("• Cleaned up test tenant data & disk files successfully.\n")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
