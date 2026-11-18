from fastapi import APIRouter
from app.api.endpoints import (
    chat,
    upload,
    documents,
    images,
    audio,
    videos,
    datasets,
    decision_support,
    conversations
)

api_router = APIRouter()

api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(images.router, prefix="/images", tags=["Images"])
api_router.include_router(audio.router, prefix="/audio", tags=["Audio"])
api_router.include_router(videos.router, prefix="/videos", tags=["Videos"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["Datasets"])
api_router.include_router(decision_support.router, prefix="/decision-support", tags=["Decision Support"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
