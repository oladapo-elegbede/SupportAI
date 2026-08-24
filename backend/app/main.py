from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import setup_logging, logger
from app.core.middleware import LoggingAndCorrelationMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info(
        "application_startup",
        app_name=settings.APP_NAME,
        env=settings.APP_ENV,
    )
    yield
    # Shutdown
    logger.info("application_shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Customer Support SaaS API using Retrieval-Augmented Generation (RAG)",
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Register logging & correlation ID middleware
app.add_middleware(LoggingAndCorrelationMiddleware)


@app.get("/")
async def root():
    return {
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "unhealthy"
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": settings.APP_NAME.lower() + "-backend",
        "environment": settings.APP_ENV,
        "database": db_status,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
    }
