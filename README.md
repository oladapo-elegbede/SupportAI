# SupportAI

An AI-Powered Customer Support SaaS platform built with Retrieval-Augmented Generation (RAG).

> **Positioning:** Full-Stack AI Engineering Portfolio Project

## Architecture Overview

SupportAI operates as a **Modular Monolith** designed for multi-tenant customer support context-grounding:

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Query
- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), Alembic
- **Database:** PostgreSQL 16 with `pgvector` extension for relational data and vector embeddings
- **Background Jobs:** ARQ + Redis job queue for asynchronous document ingestion
- **AI Runtime:** Ollama (local) hosting `qwen2.5:3b` / `llama3.2:1b` (LLM) and `nomic-embed-text` (Embeddings)
- **Storage:** Abstracted file storage (Local File Storage for dev)

## Repository Structure

```text
supportai/
├── backend/       # FastAPI application, services, models, migrations
├── frontend/      # React + TypeScript Vite frontend
├── infra/         # Docker Compose and local infrastructure configurations
├── docs/          # Architecture specs, system design, and decision records
└── uploads/       # Storage directory for ingested document files
Setup & Local Development
Detailed environment setup and run instructions will be updated as foundation phases complete.

License
MIT
