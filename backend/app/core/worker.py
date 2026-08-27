import uuid
import structlog
from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.ingestion import IngestionService

logger = structlog.get_logger("supportai.worker")


def parse_redis_settings(url: str) -> RedisSettings:
    host = "localhost"
    port = 6379
    if "://" in url:
        part = url.split("://")[1].split("/")[0]
        if ":" in part:
            host, port_str = part.split(":")
            port = int(port_str)
        else:
            host = part
    return RedisSettings(host=host, port=port)


redis_settings = parse_redis_settings(settings.REDIS_URL)


async def startup(ctx):
    logger.info("arq_worker_startup", host=redis_settings.host, port=redis_settings.port)


async def shutdown(ctx):
    logger.info("arq_worker_shutdown")


async def process_document_task(ctx, document_id: str, organization_id: str):
    """ARQ background task executing full document ingestion."""
    logger.info(
        "processing_document_task_started",
        document_id=document_id,
        organization_id=organization_id,
    )
    doc_uuid = uuid.UUID(document_id)
    org_uuid = uuid.UUID(organization_id)

    async with AsyncSessionLocal() as session:
        service = IngestionService(session)
        success = await service.process_document(doc_uuid, org_uuid)

    logger.info("processing_document_task_finished", document_id=document_id, success=success)
    return success


class WorkerSettings:
    functions = [process_document_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings
    max_jobs = 10
    job_timeout = 600
