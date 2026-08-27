# SupportAI

An AI-Powered Customer Support SaaS platform built with Retrieval-Augmented Generation (RAG).

> **Positioning:** Full-Stack AI Engineering Portfolio Project  
> **Development Cost:** ₦0 (100% Local Development Stack)

---

## Architecture Overview

SupportAI operates as a **Modular Monolith** designed for multi-tenant customer support grounding:

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS
- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), Alembic
- **Database:** PostgreSQL 16 with `pgvector` extension for relational data and vector embeddings
- **Job Broker:** Redis 7 + ARQ async worker
- **AI Runtime:** Ollama (native host) running `qwen2.5:3b` (LLM) and `nomic-embed-text` (768-dim Embeddings)
- **Logging:** `structlog` with JSON formatting and `X-Request-ID` correlation middleware

---

## Repository Structure

```text
supportai/
├── backend/            # FastAPI backend application
│   ├── alembic/        # Async database migrations
│   ├── app/
│   │   ├── core/       # Config, database, logging, middleware
│   │   └── main.py     # Application entrypoint
│   └── scripts/        # Hardware benchmarking and dev utilities
├── frontend/           # React + TypeScript Vite client
├── infra/              # Docker Compose infrastructure (PostgreSQL + Redis)
├── docs/               # Architecture specs and decision records
└── uploads/            # Local document storage directory

Local Development Setup (₦0 Stack)
Prerequisites
Docker Desktop
Node.js 20+
Python 3.11+
Ollama (installed natively on host)
1. Infrastructure (PostgreSQL + Redis)
PowerShell

docker compose -f infra/docker-compose.yml up -d
2. AI Models (Ollama)
PowerShell

ollama pull nomic-embed-text
ollama pull qwen2.5:3b
3. Backend Setup
PowerShell

cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
4. Frontend Setup
PowerShell

cd frontend
npm install
npm run dev
Frontend: http://localhost:5173
Backend API Docs: http://localhost:8000/docs
Health Check: http://localhost:8000/health
Hardware Benchmark Results (Intel i5-8th Gen, 8GB RAM, CPU)
text

• Embedding Model: nomic-embed-text (768 dimensions)
• Primary LLM: qwen2.5:3b
• Generation Speed: ~6.6 tokens/sec
• RAG Accuracy: Grounded (no hallucination)
License
MIT