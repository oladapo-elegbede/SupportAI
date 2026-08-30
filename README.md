# SupportAI — AI-Powered Customer Support SaaS

> **Full-Stack AI Engineer Portfolio Project**
>
> A multi-tenant customer-support platform that uses Retrieval-Augmented Generation (RAG) to produce grounded answers from organization-specific documentation.

**Local Development Cost:** ₦0
**AI Runtime:** Ollama / Open-weight models
**Architecture:** Modular monolith + asynchronous ingestion
**Primary Focus:** RAG, multi-tenancy, security, vector search, evaluation

---

## Overview

SupportAI is a full-stack AI customer-support SaaS designed around a simple problem:

**How can a business give an AI assistant access to its own documentation and receive answers grounded in that documentation rather than relying entirely on the model's general knowledge?**

The system allows organizations to create knowledge bases, upload support documentation, process those documents asynchronously, generate vector embeddings, store them in PostgreSQL with `pgvector`, and use semantic retrieval to construct grounded responses.

The project was intentionally built with a **local, open-source AI stack**, allowing the complete system to run without paid AI APIs.

---

## What I Built

### AI & RAG

- Retrieval-Augmented Generation pipeline
- Document ingestion and processing
- Text extraction and chunking
- Vector embeddings
- PostgreSQL + pgvector vector search
- HNSW vector index
- Context-aware answer generation
- Document-grounded citations
- Refusal behavior when retrieved context is insufficient
- Local LLM inference using Ollama
- Local RAG evaluation benchmark

### SaaS Architecture

- Multi-tenant organization architecture
- Organization-level data isolation
- Knowledge bases
- Document management
- Conversations and messages
- Customer-support chat interface
- Modular service architecture

### Security

- JWT-based authentication
- Short-lived access tokens
- Long-lived refresh sessions
- HttpOnly refresh cookies
- SameSite cookie protection
- Refresh-token rotation
- Refresh-token reuse detection
- Password hashing
- Tenant isolation
- Path traversal protection
- Prompt-injection guardrails

### Backend & Infrastructure

- FastAPI
- SQLAlchemy 2.0 async ORM
- PostgreSQL 16
- pgvector
- Redis
- ARQ background workers
- Alembic migrations
- Docker-based infrastructure
- Provider abstraction for AI and storage services

### Frontend

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Authentication flows
- Knowledge-base management
- Document management
- AI chat interface
- Loading, error and empty states

---

# Architecture

```text
                           ┌─────────────────────────┐
                           │       React Client      │
                           │ React + TypeScript      │
                           │ Vite + Tailwind         │
                           └────────────┬────────────┘
                                        │
                              HTTPS / JWT + Cookie
                                        │
                                        ▼
                           ┌─────────────────────────┐
                           │      FastAPI API        │
                           │                         │
                           │ Auth / KB / Documents   │
                           │ Chat / Organizations    │
                           └────────────┬────────────┘
                                        │
                                        ▼
                           ┌─────────────────────────┐
                           │      Service Layer      │
                           │                         │
                           │ AuthService              │
                           │ KBService                │
                           │ DocumentService          │
                           │ IngestionService         │
                           │ RetrievalService         │
                           │ ChatService              │
                           └──────┬──────────┬───────┘
                                  │          │
                    ┌─────────────┘          └──────────────┐
                    ▼                                       ▼
          ┌──────────────────┐                    ┌──────────────────┐
          │ Provider Layer   │                    │ Background Jobs  │
          │                  │                    │                  │
          │ LLM Provider     │                    │ Redis + ARQ      │
          │ Embedding        │                    │ Ingestion Worker │
          │ File Storage     │                    └────────┬─────────┘
          └────────┬─────────┘                             │
                   │                                       │
                   ▼                                       ▼
          ┌──────────────────┐                    ┌──────────────────┐
          │     Ollama       │                    │   PostgreSQL     │
          │                  │                    │                  │
          │ qwen2.5:3b       │                    │ Users            │
          │ nomic-embed-text │                    │ Organizations     │
          └──────────────────┘                    │ Knowledge Bases  │
                                                  │ Documents        │
                                                  │ Chunks + Vectors │
                                                  │ Conversations    │
                                                  │ Messages         │
                                                  └──────────────────┘

The application follows a modular monolith architecture.

The API layer handles HTTP concerns while business logic is isolated inside services. Provider abstractions prevent the application from being tightly coupled to a particular AI or storage implementation.

RAG Pipeline

The core AI workflow is:

Document Upload
      │
      ▼
Validation
      │
      ▼
Document Storage
      │
      ▼
Background Ingestion
      │
      ▼
Text Extraction
      │
      ▼
Text Chunking
      │
      ▼
Embedding Generation
      │
      ▼
PostgreSQL + pgvector
      │
      ▼
Semantic Retrieval
      │
      ▼
Context Construction
      │
      ▼
LLM Generation
      │
      ▼
Grounded Answer
      │
      ▼
Document Citations

This separates document processing from user-facing API requests.

Uploading a document does not require the API request to perform the entire ingestion pipeline synchronously. Redis and ARQ are used to execute ingestion work in the background.

AI Architecture

SupportAI uses provider abstractions so that the application is not tightly coupled to one model vendor.

                 Application
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
   EmbeddingService          LLMService
          │                       │
          ▼                       ▼
      Ollama                  Ollama
          │                       │
          ▼                       ▼
 nomic-embed-text            qwen2.5:3b
Embeddings

The local embedding stack uses:

nomic-embed-text

with 768-dimensional embeddings.

LLM

The local language model is:

qwen2.5:3b

running through Ollama.

The provider abstraction makes it possible to evolve the implementation toward hosted model providers in a future production deployment without rewriting the application's core business logic.

Vector Search

SupportAI uses:

PostgreSQL 16
        +
pgvector

instead of introducing a separate vector database.

The system uses an HNSW index with cosine distance for similarity search.

This approach keeps relational application data and vector data within the same database while reducing infrastructure complexity for the project.

Multi-Tenancy

SupportAI is designed as a multi-tenant SaaS application.

The organization is the primary tenant boundary.

A simplified relationship is:

Organization
    │
    ├── Users / Members
    │
    ├── Knowledge Bases
    │       │
    │       └── Documents
    │               │
    │               └── Chunks + Embeddings
    │
    └── Conversations
            │
            └── Messages

Tenant identity is derived from authenticated user context rather than trusting arbitrary organization identifiers supplied by the client.

Database queries, vector retrieval and file operations are scoped to the authenticated organization.

This prevents one organization's data from being unintentionally exposed to another organization.

Security Architecture

Security was treated as part of the application architecture rather than an afterthought.

Authentication
Short-lived access JWTs
Long-lived refresh sessions
HttpOnly refresh cookies
SameSite cookie protection
Refresh-token rotation
Refresh-token reuse detection
Token-family revocation
Password hashing
Tenant Isolation

Client-supplied organization identifiers are not treated as authoritative for authorization decisions.

The authenticated organization context determines which resources the user can access.

File Security

Uploaded files are renamed using generated document identifiers and storage paths are validated to remain within the intended upload directory.

This mitigates path traversal attacks.

Prompt Injection Guardrails

Retrieved material is explicitly separated from system instructions using structured context boundaries.

The generation layer also includes deterministic refusal behavior when the available context is insufficient to answer a question reliably.

RAG Evaluation

SupportAI includes a local evaluation suite rather than relying only on subjective chatbot testing.

The current benchmark contains 5 ground-truth test cases.

Current Local Benchmark
Metric    Score    Target    Status
Context Retrieval Hit@3    100.0%    >= 90%    PASS
Mean Reciprocal Rank (MRR)    1.00    >= 0.85    PASS
Answer Keyword Recall    100.0%    >= 80%    PASS
Refusal Guardrail Correctness    100.0%    100%    PASS
What the Metrics Mean

Hit@3
Measures whether a relevant document chunk appears within the top three retrieved results.

MRR
Measures how highly the first relevant result is ranked.

Keyword Recall
Measures whether expected answer concepts appear in the generated response.

Refusal Accuracy
Measures whether the system correctly refuses questions when the available context is insufficient.

These results describe the current local benchmark. They should not be interpreted as proof of universal model or retrieval accuracy.

Local Performance

The following measurements were recorded on the development machine:

Hardware

Intel Core i5 8th Generation
8 GB RAM
CPU-only inference
Measurements
Operation    Observed Local Performance
Embedding latency    ~50–150 ms / chunk
LLM generation    ~6.6 tokens/sec
Grounded response    ~3–5 seconds

These are local development measurements, not production-scale performance benchmarks.

The primary purpose is to demonstrate that the complete RAG pipeline can run locally without paid AI APIs.

Engineering Decisions
Decision    Reason
PostgreSQL + pgvector    Keeps relational and vector data in one database
HNSW    Efficient approximate nearest-neighbor vector search
Redis + ARQ    Moves document ingestion away from synchronous API requests
Ollama    Enables local, zero-cost model inference
FastAPI    Async-friendly Python API framework with strong validation
SQLAlchemy 2.0 Async    Structured database access with asynchronous application support
Modular monolith    Keeps domain boundaries clear without unnecessary distributed-system complexity
Provider abstractions    Allows AI/storage implementations to change without rewriting business logic
Local evaluation suite    Makes RAG quality measurable instead of relying only on manual testing
Asynchronous Ingestion

Document ingestion is handled outside the request/response path.

Client
  │
  │ Upload document
  ▼
FastAPI
  │
  ├── Validate
  ├── Persist metadata
  └── Enqueue ingestion job
             │
             ▼
          Redis
             │
             ▼
         ARQ Worker
             │
       ┌─────┴─────┐
       ▼           ▼
 Text Extraction  Chunking
       │           │
       └─────┬─────┘
             ▼
        Embeddings
             │
             ▼
       pgvector Storage

This prevents potentially expensive document processing from blocking the API request.

Testing

The backend includes automated unit and integration testing using:

pytest
pytest-cov

The current test suite contains approximately 24 unit and integration tests.

Testing covers important areas including:

application health
authentication behavior
database interactions
document/knowledge-base workflows
RAG behavior
service-layer behavior
ingestion behavior
security-related logic

Run the suite with:

cd backend
.\.venv\Scripts\Activate.ps1
pytest
Project Structure
SupportAI/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── providers/
│   │   ├── prompts/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── tasks/
│   │
│   ├── alembic/
│   ├── tests/
│   └── scripts/
│
├── frontend/
│   └── src/
│
├── infra/
│   └── docker-compose.yml
│
├── README.md
└── LICENSE

The backend is organized around domain responsibilities rather than placing all application logic inside route handlers.

Technology Stack
Frontend
React 18
TypeScript
Vite
Tailwind CSS
Backend
Python 3.11+
FastAPI
Pydantic v2
SQLAlchemy 2.0 Async
Alembic
Data
PostgreSQL 16
pgvector
Redis
Background Processing
ARQ
Redis
AI
Ollama
qwen2.5:3b
nomic-embed-text
Infrastructure
Docker
Docker Compose
Local Development

SupportAI was intentionally designed to run locally without paid AI APIs.

Prerequisites
Docker Desktop
Node.js 20 LTS+
Python 3.11+
Ollama
1. Start Infrastructure
docker compose -f infra/docker-compose.yml up -d
2. Provision Local AI Models
ollama pull nomic-embed-text
ollama pull qwen2.5:3b
3. Setup Backend
cd backend

python -m venv .venv

.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
4. Apply Database Migrations
alembic upgrade head
5. Start FastAPI
uvicorn app.main:app --reload --port 8000
6. Start Background Worker

Open another PowerShell terminal:

cd backend

.\.venv\Scripts\Activate.ps1

arq app.core.worker.WorkerSettings
7. Start Frontend

Open another terminal:

cd frontend

npm install

npm run dev
Local Services
Service    URL
Frontend    http://localhost:5173
FastAPI    http://localhost:8000
API Documentation    http://localhost:8000/docs
Health Check    http://localhost:8000/health
API Overview

The API is organized around several major domains.

Authentication
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
Organizations

Organization and membership endpoints manage tenant boundaries and user access.

Knowledge Bases

Knowledge bases provide logical containers for organization documentation.

Documents

Document endpoints manage uploading and processing support content.

Chat

Chat endpoints retrieve relevant document context and generate grounded answers.

Health
GET /health

Interactive API documentation is available through FastAPI's OpenAPI interface:

http://localhost:8000/docs
Production Evolution

SupportAI currently runs locally and does not claim to be deployed production infrastructure.

The architecture was designed so that individual infrastructure components can be replaced as the system evolves.

LOCAL DEVELOPMENT                 POSSIBLE PRODUCTION

PostgreSQL + pgvector       →     Managed PostgreSQL
Local file storage          →     Amazon S3
Redis + ARQ                 →     Managed queue/workers
Ollama                      →     Bedrock / hosted inference
Docker Compose              →     ECS / container platform
Local monitoring            →     CloudWatch / observability stack

These are proposed production evolution paths, not components currently deployed by this repository.

Known Limitations

SupportAI is a portfolio project and therefore has several deliberate limitations.

The AI inference stack runs locally through Ollama.
The current LLM benchmark uses CPU-only inference.
The RAG evaluation dataset is intentionally small.
Local file storage is used instead of production object storage.
The current deployment is local rather than publicly hosted.
The evaluation benchmark should be expanded before making claims about large-scale retrieval quality.
Production-scale load testing has not been performed.

These limitations are intentional boundaries of the current portfolio implementation rather than hidden assumptions.

What This Project Demonstrates

SupportAI was built to demonstrate practical AI application engineering across several layers of a real software system.

AI Engineering
Retrieval-Augmented Generation
Embeddings
Vector search
Grounded generation
Prompt-injection defenses
RAG evaluation
Backend Engineering
FastAPI
Async database access
Service-layer architecture
Background processing
PostgreSQL
Redis
Full-Stack Engineering
React
TypeScript
API integration
Authentication flows
SaaS dashboard architecture
Security Engineering
JWT sessions
Refresh-token rotation
Tenant isolation
Cookie security
Password hashing
File-system security
Systems Thinking

The project is intentionally more than a chatbot UI.

It demonstrates how an AI feature can be integrated into a larger software system with:

Authentication
      +
Multi-tenancy
      +
Document Processing
      +
Background Jobs
      +
Vector Retrieval
      +
LLM Inference
      +
Security
      +
Evaluation
Portfolio Demo

A technical walkthrough video will be added here.

📺 Demo video: Coming soon

The planned demonstration will show:

Organization and authentication flow
Knowledge-base creation
Document upload
Background document ingestion
Vector retrieval
Grounded AI responses
Document citations
RAG evaluation
Security architecture
Local AI inference
License

This project is released under the MIT License.

See LICENSE for details.
