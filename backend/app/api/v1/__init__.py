from app.api.v1.auth import router as auth_router
from app.api.v1.knowledge_base import router as kb_router
from app.api.v1.document import router as doc_router
from app.api.v1.chat import router as chat_router
from app.api.v1.public_chat import router as public_chat_router

__all__ = ["auth_router", "kb_router", "doc_router", "chat_router", "public_chat_router"]
