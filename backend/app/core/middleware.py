import uuid
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.core.config import settings

logger = structlog.get_logger("supportai.http")


class LoggingAndCorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware that injects X-Request-ID and logs request start/finish timing."""
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that attaches security hardening headers to all HTTP responses."""
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Hardening Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        if settings.APP_ENV != "development":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
