from app.api.v1.auth import router as auth_router
from app.api.v1.knowledge_base import router as kb_router
from app.api.v1.document import router as doc_router

__all__ = ["auth_router", "kb_router", "doc_router"]
