# SupportAI — AI-Powered Customer Support SaaS (RAG)

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue?logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue?logo=typescript)](https://www.typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%2Bpgvector-blue?logo=postgresql)](https://github.com/pgvector/pgvector)
[![Ollama](https://img.shields.io/badge/Ollama-Local_AI-orange?logo=ollama)](https://ollama.com)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

> **Positioning:** Full-Stack AI Engineer Portfolio Showcase  
> **Local Development Cost:** ₦0 /  (100% Local Open-Source AI Stack)

SupportAI is a production-grade, multi-tenant B2B SaaS platform that enables businesses to upload their support documentation (PDFs, TXT) and deploy an AI customer support agent that delivers accurate, grounded answers with verified document citations using Retrieval-Augmented Generation (RAG).

---

## 🌟 Executive Summary & Engineering Highlights

- **Modular Monolith Architecture:** Clean separation across API routes, Pydantic v2 schemas, business services, security primitives, and SQLAlchemy 2.0 async ORM.
- **Row-Level Tenant Isolation:** Strict organization-level data boundaries. Every database query, vector search, and file operation is scoped to \organization_id\ derived exclusively from cryptographically verified JWT claims.
- **Local Open-Weight AI Stack (₦0 Cost):** Uses **Ollama** running locally on host CPU:
  - **Embedding Model:** omic-embed-text\ (768-dimensional float vectors).
  - **LLM Model:** \qwen2.5:3b\ (Q4_K_M quantized) for high-precision RAG instruction following.
- **Native Vector Database:** PostgreSQL 16 with \pgvector\ and HNSW Cosine Distance (\<=>\) index (\m=16\, \ef_construction=64\).
- **Asynchronous Ingestion Engine:** Non-blocking file uploads via **ARQ + Redis** background worker queue.
- **Hardened Session Security:** Short-lived (30-min) in-memory access JWTs + long-lived (7-day) \httpOnly\ refresh cookies with token rotation, 5-second concurrency grace periods, and automatic token family reuse revocation.
- **Prompt Injection Guardrails:** XML context delimitation (\<reference_material>\), role framing, and deterministic refusal rules when context is insufficient.
- **Local RAG Evaluation Suite:** Deterministic benchmark suite measuring Hit@3, MRR, Keyword Recall, and Refusal Accuracy locally without paid APIs.

---

## 📐 System Architecture

\\	ext
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND CLIENT                        │
│             React 18 + TypeScript + Vite                    │
│            Tailwind CSS + In-Memory Auth                    │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS (Bearer JWT + httpOnly Cookie)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 FASTAPI BACKEND APPLICATION                 │
│                     (Modular Monolith)                      │
│                                                             │
│  ┌──────────────┐  ┌─────────────────┐  ┌────────────────┐ │
│  │ Auth Routes  │  │ KB / Doc Routes │  │ Chat Routes    │ │
│  └──────┬───────┘  └────────┬────────┘  └───────┬────────┘ │
│         │                   │                   │          │
│  ┌──────▼───────────────────▼───────────────────▼────────┐ │
│  │                   SERVICE LAYER                       │ │
│  │   AuthService     DocumentService    RetrievalService │ │
│  │   KBService       IngestionService   ChatService      │ │
│  └──────┬───────────────────┬───────────────────┬────────┘ │
│         │                   │                   │          │
│  ┌──────▼───────────────────▼───────────────────▼────────┐ │
│  │               PROVIDER ABSTRACTIONS                   │ │
│  │  FileStorage          EmbeddingService   LLMService   │ │
│  │  (LocalFileStorage)   (Ollama Provider)  (Ollama)     │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────┬───────────────────┬───────────────────┬──────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐
│  PostgreSQL 16   │  │   Redis 7    │  │  Ollama Native   │
│   + pgvector     │  │ (ARQ Broker) │  │                  │
│                  │  └──────┬───────┘  │ • qwen2.5:3b     │
│ • users / orgs   │         │          │ • nomic-embed    │
│ • knowledge_base │         ▼          └──────────────────┘
│ • documents      │  ┌──────────────┐
│ • chunks+vectors │  │  ARQ Worker  │
│ • conversations  │  │  Ingestion   │
│ • messages       │  └──────────────┘
└──────────────────┘
\
---

## 📊 Local RAG Quality Evaluation Benchmark

Measured locally via \python scripts/evaluate_rag.py\ across 5 ground-truth test cases:

| Metric | Measured Score | Target Benchmark | Status |
|---|---|---|---|
| **Context Retrieval Hit Rate (Hit@3)** | **100.0%** | >= 90% | **PASS** |
| **Mean Reciprocal Rank (MRR)** | **1.00** | >= 0.85 | **PASS** |
| **Answer Keyword Recall** | **100.0%** | >= 80% | **PASS** |
| **Refusal Guardrail Correctness** | **100.0%** | 100% | **PASS** |

### Verified Hardware Performance (Intel i5 8th Gen, 8GB RAM, CPU-Only):
- **Vector Embedding Latency:** ~50–150ms per chunk (omic-embed-text\).
- **LLM Token Generation Rate:** ~6.6 tokens/sec (\qwen2.5:3b\).
- **Average Grounded Response Time:** ~3–5 seconds (warm RAM start).

---

## 🛠️ Local Development Setup (₦0 Stack)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Node.js 20 LTS+](https://nodejs.org)
- [Python 3.11+](https://www.python.org)
- [Ollama](https://ollama.com/download/windows) (installed natively on host)

### 1. Start Infrastructure Containers (PostgreSQL + Redis)
\\powershell
docker compose -f infra/docker-compose.yml up -d
\
### 2. Provision Local AI Models in Ollama
\\powershell
ollama pull nomic-embed-text
ollama pull qwen2.5:3b
\
### 3. Setup & Run Backend API Server
\\powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Apply database migrations
alembic upgrade head

# Start FastAPI application
uvicorn app.main:app --reload --port 8000
\
### 4. Start Background Ingestion Worker (New Terminal)
\\powershell
cd backend
.\.venv\Scripts\Activate.ps1
arq app.core.worker.WorkerSettings
\
### 5. Setup & Run React Frontend Client (New Terminal)
\\powershell
cd frontend
npm install
npm run dev
\
- **Frontend Client:** \http://localhost:5173- **Interactive OpenAPI Specs:** \http://localhost:8000/docs- **Health Check Endpoint:** \http://localhost:8000/health
---

## 🧪 Running Automated Tests

Run the full backend test suite covering 24 unit & integration tests:

\\powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
\
---

## 🛡️ Security & Tenant Isolation Controls

1. **Strict Tenant Boundaries:** Front-end supplied \organization_id\s are never trusted. All database queries filter explicitly on \current_user.organization_id\.
2. **Credential Safety:** Passwords hashed with \crypt\ (cost factor 12). \password_hash\ is excluded from all Pydantic response models.
3. **Session Theft Protection:** Refresh tokens are stored exclusively as SHA-256 hashes in PostgreSQL. Re-using an already-rotated token triggers automatic family revocation, terminating the attacker's session.
4. **XSS & CSRF Defense:** Access tokens remain in React memory state. Refresh tokens delivered via \httpOnly\, \SameSite=Lax\ cookies.
5. **Path Traversal Defense:** Uploaded files renamed to \{doc_id}.{ext}\ on disk; \LocalFileStorage\ verifies target paths strictly remain within \./uploads\.

---

## 📄 License

This project is open-source software licensed under the [MIT License](LICENSE).