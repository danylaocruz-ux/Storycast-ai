from .auth import router as auth_router
from .books import router as books_router
from .characters import router as characters_router
from .audio import router as audio_router

__all__ = ["auth_router", "books_router", "characters_router", "audio_router"]
