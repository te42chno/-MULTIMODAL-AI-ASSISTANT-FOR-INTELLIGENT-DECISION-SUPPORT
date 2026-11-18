import json
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
VECTOR_DIR = DATA_DIR / "vector_store"
DB_PATH = DATA_DIR / "assistant.db"


def _database_url() -> str:
    """Resolve DATABASE_URL, ignoring documentation placeholders.

    A copy/pasted example URL such as ``...USER:PASSWORD@EP-HOST...`` cannot be
    connected to. Falling back to local SQLite keeps the app usable instead of
    crashing every request at import time. Real Postgres URLs are untouched.
    """
    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        return f"sqlite:///{DB_PATH}"
    lowered = raw.lower()
    if "ep-host" in lowered or "user:password@" in lowered:
        return f"sqlite:///{DB_PATH}"
    return raw


DATABASE_URL = _database_url()

# Serverless filesystems are read-only outside /tmp, and database-backed storage
# does not need local directories at all. Never fail application import over this.
if os.getenv("STORAGE_BACKEND", "local").lower() != "database" or DATABASE_URL.startswith("sqlite"):
    for p in [
        DATA_DIR,
        UPLOAD_DIR,
        UPLOAD_DIR / "documents",
        UPLOAD_DIR / "images",
        UPLOAD_DIR / "audio",
        UPLOAD_DIR / "videos",
        UPLOAD_DIR / "datasets",
        VECTOR_DIR,
    ]:
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_list(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    except Exception:
        pass
    return [x.strip() for x in raw.split(",") if x.strip()]


class Settings(BaseModel):
    PROJECT_NAME: str = "MedReason — Clinical Multimodal RAG Assistant"
    API_V1_PREFIX: str = "/api"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() in {"1", "true", "yes"}

    #LLM: mock | gemini | openai | groq | ollama
    LLM_PROVIDER: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "mock").lower())
    LLM_MODEL: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "qwen/qwen3.8-27b"))
    LLM_API_KEY: str = Field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))

    # VLM: mock | gemini | openai
    VISION_PROVIDER: str = Field(default_factory=lambda: os.getenv("VISION_PROVIDER", "gemini").lower())
    VISION_MODEL: str = Field(default_factory=lambda: os.getenv("VISION_MODEL", "gemini-flash-lite-latest"))
    VISION_API_KEY: str = Field(default_factory=lambda: os.getenv("VISION_API_KEY", ""))

    # ASR: local | whisper | mock
    SPEECH_PROVIDER: str = Field(default_factory=lambda: os.getenv("SPEECH_PROVIDER", "local").lower())
    WHISPER_MODEL: str = Field(default_factory=lambda: os.getenv("WHISPER_MODEL", "base"))

    # hashing_cosine | local_transformers
    EMBEDDING_PROVIDER: str = Field(
        default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "hashing_cosine").lower()
    )
    EMBEDDING_MODEL: str = Field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))

    MAX_UPLOAD_SIZE_BYTES: int = Field(
        default_factory=lambda: _env_int("MAX_UPLOAD_SIZE_BYTES", 50 * 1024 * 1024)
    )
    MAX_VIDEO_DURATION_SECONDS: int = Field(
        default_factory=lambda: _env_int("MAX_VIDEO_DURATION_SECONDS", 180)
    )
    VIDEO_FRAME_INTERVAL_SECONDS: int = Field(
        default_factory=lambda: _env_int("VIDEO_FRAME_INTERVAL_SECONDS", 2)
    )

    # Serverless deployments (e.g. Vercel) must supply an external Postgres URL;
    # the default SQLite file is for local development only.
    DATABASE_URL: str = Field(default_factory=lambda: DATABASE_URL)

    # local      -> keep uploads on the local filesystem (development)
    # database   -> persist upload bytes in the DB and stage them in /tmp (serverless)
    STORAGE_BACKEND: str = Field(
        default_factory=lambda: os.getenv("STORAGE_BACKEND", "local").lower()
    )
    TEMP_DIR: str = Field(default_factory=lambda: os.getenv("TEMP_DIR", "/tmp/medreason"))

    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: _env_list(
            "CORS_ORIGINS",
            [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ],
        )
    )


settings = Settings()
