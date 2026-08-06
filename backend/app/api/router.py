from fastapi import APIRouter

from backend.app.api.endpoints import (
    audio,
    auth,
    chat,
    documents,
    health,
    search,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(search.router)
api_router.include_router(chat.router)
api_router.include_router(audio.router)
