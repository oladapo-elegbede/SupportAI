from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog

from app.services.auth import AuthError, InvalidCredentialsError, InvalidTokenError
from app.services.knowledge_base import KBError, KBNotFoundError, KBAlreadyExistsError
from app.services.document import DocumentError, DocumentNotFoundError, FileValidationError
from app.services.storage import StorageError, PathTraversalError
from app.services.chat import ChatError
from app.services.llm import LLMError
from app.services.embedding import EmbeddingError

logger = structlog.get_logger("supportai.exceptions")


def format_error_response(
    code: str,
    message: str,
    request_id: Optional[str] = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: Optional[Any] = None,
) -> JSONResponse:
    """Helper to construct standard JSON error payload."""
    payload: Dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }
    if details is not None:
        payload["error"]["details"] = details

    return JSONResponse(status_code=status_code, content=payload)


def register_exception_handlers(app: FastAPI) -> None:
    """Registers global exception handlers on the FastAPI app."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = request.headers.get("X-Request-ID")
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            413: "PAYLOAD_TOO_LARGE",
            429: "TOO_MANY_REQUESTS",
            500: "INTERNAL_SERVER_ERROR",
        }
        code = code_map.get(exc.status_code, "HTTP_ERROR")
        detail_msg = exc.detail if isinstance(exc.detail, str) else "HTTP Request Error"

        return format_error_response(
            code=code,
            message=detail_msg,
            request_id=request_id,
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = request.headers.get("X-Request-ID")
        # Extract clean error messages from Pydantic validation errors
        formatted_details = []
        for error in exc.errors():
            loc = " -> ".join([str(x) for x in error.get("loc", []) if x != "body"])
            formatted_details.append({
                "field": loc,
                "message": error.get("msg", "Invalid value"),
            })

        return format_error_response(
            code="VALIDATION_ERROR",
            message="Request validation failed. Please check input parameters.",
            request_id=request_id,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=formatted_details,
        )

    @app.exception_handler(AuthError)
    async def auth_exception_handler(request: Request, exc: AuthError):
        request_id = request.headers.get("X-Request-ID")
        if isinstance(exc, InvalidCredentialsError):
            return format_error_response(
                code="INVALID_CREDENTIALS",
                message=str(exc),
                request_id=request_id,
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        elif isinstance(exc, InvalidTokenError):
            return format_error_response(
                code="INVALID_TOKEN",
                message=str(exc),
                request_id=request_id,
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        return format_error_response(
            code="AUTH_ERROR",
            message=str(exc),
            request_id=request_id,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    @app.exception_handler(KBError)
    async def kb_exception_handler(request: Request, exc: KBError):
        request_id = request.headers.get("X-Request-ID")
        if isinstance(exc, KBNotFoundError):
            return format_error_response(
                code="KNOWLEDGE_BASE_NOT_FOUND",
                message=str(exc),
                request_id=request_id,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        elif isinstance(exc, KBAlreadyExistsError):
            return format_error_response(
                code="KNOWLEDGE_BASE_ALREADY_EXISTS",
                message=str(exc),
                request_id=request_id,
                status_code=status.HTTP_409_CONFLICT,
            )
        return format_error_response(
            code="KNOWLEDGE_BASE_ERROR",
            message=str(exc),
            request_id=request_id,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    @app.exception_handler(DocumentError)
    async def document_exception_handler(request: Request, exc: DocumentError):
        request_id = request.headers.get("X-Request-ID")
        if isinstance(exc, DocumentNotFoundError):
            return format_error_response(
                code="DOCUMENT_NOT_FOUND",
                message=str(exc),
                request_id=request_id,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        elif isinstance(exc, FileValidationError):
            return format_error_response(
                code="INVALID_FILE_FORMAT",
                message=str(exc),
                request_id=request_id,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return format_error_response(
            code="DOCUMENT_ERROR",
            message=str(exc),
            request_id=request_id,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    @app.exception_handler(PathTraversalError)
    async def path_traversal_handler(request: Request, exc: PathTraversalError):
        request_id = request.headers.get("X-Request-ID")
        logger.error("security_path_traversal_blocked", request_id=request_id, error=str(exc))
        return format_error_response(
            code="SECURITY_VIOLATION",
            message="Access denied: invalid file path.",
            request_id=request_id,
            status_code=status.HTTP_403_FORBIDDEN,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = request.headers.get("X-Request-ID")
        logger.error(
            "unhandled_server_exception",
            request_id=request_id,
            error=str(exc),
            exc_info=True,
        )
        return format_error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred. Please contact support.",
            request_id=request_id,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
