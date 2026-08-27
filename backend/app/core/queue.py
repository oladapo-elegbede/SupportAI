import uuid
import structlog
from arq import create_pool
from arq.connections import RedisSettings
from app.core.config import settings

logger = structlog.get_logger("supportai.queue")


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


async def enqueue_ingestion_job(document_id: uuid.UUID, organization_id: uuid.UUID) -> str | None:
    """Enqueues a document ingestion task into Redis for the ARQ worker."""
    try:
        redis = await create_pool(redis_settings)
        job = await redis.enqueue_job(
            "process_document_task",
            str(document_id),
            str(organization_id),
        )
        logger.info(
            "ingestion_job_enqueued",
            document_id=str(document_id),
            organization_id=str(organization_id),
            job_id=job.job_id if job else None,
        )
        return job.job_id if job else None
    except Exception as e:
        logger.error(
            "ingestion_job_enqueue_failed",
            document_id=str(document_id),
            error=str(e),
        )
        return None
