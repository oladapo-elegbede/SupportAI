import uuid
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger("supportai.http")


class LoggingAndCorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract existing X-Request-ID header or generate a new UUID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Bind correlation ID to structlog contextvars for this request thread
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start_time = time.perf_counter()

        logger.info(
            "http_request_started",
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else "unknown",
        )

        try:
            response = await call_next(request)
            process_time = (time.perf_counter() - start_time) * 1000

            logger.info(
                "http_request_finished",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(process_time, 2),
            )

            # Return X-Request-ID back in response headers
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as exc:
            process_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                "http_request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(process_time, 2),
                error=str(exc),
                exc_info=True,
            )
            raise exc
