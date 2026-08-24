from fastapi import FastAPI

app = FastAPI(
    title="SupportAI API",
    description="AI-Powered Customer Support SaaS API using Retrieval-Augmented Generation (RAG)",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {
        "message": "SupportAI API is running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "supportai-backend",
    }
