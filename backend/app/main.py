import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.config import settings, UPLOAD_DIR
from app.database import init_db
from app.api.router import api_router


# Ensure tables exist for both uvicorn and in-process TestClient usage.
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Clinical multimodal RAG assistant for evidence-grounded document, image, audio, video and tabular analysis.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Local development only: media previews need a persistent filesystem.
if settings.STORAGE_BACKEND == "local" and UPLOAD_DIR.exists():
    app.mount("/static/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Include API endpoints under /api
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/api/health", tags=["System"])
def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "vision_provider": settings.VISION_PROVIDER,
        "speech_provider": settings.SPEECH_PROVIDER,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "database": "PostgreSQL (initialized)"
        if settings.DATABASE_URL.startswith(("postgres", "postgresql"))
        else "SQLite (initialized)",
        "storage_backend": settings.STORAGE_BACKEND,
    }


# --- Single-service hosting (Render, Railway, etc.) -------------------------
# When the React build exists, serve it from the same origin as the API so one
# web service runs the entire application. Registered last so every /api route,
# /docs and the upload mount above keep priority.
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        candidate = (FRONTEND_DIST / full_path).resolve()
        if candidate.is_file() and FRONTEND_DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
