import re
import os
from pathlib import Path
from typing import Set

ALLOWED_EXTENSIONS: Set[str] = {
    # Documents
    "pdf", "docx", "doc", "txt", "md",
    # Images
    "png", "jpg", "jpeg", "webp", "bmp",
    # Audio
    "mp3", "wav", "m4a", "ogg", "webm",
    # Video
    "mp4", "mov", "avi", "mkv",
    # Datasets
    "csv", "xlsx", "xls"
}

ALLOWED_MIME_PREFIXES: Set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
    "text/markdown",
    "image/",
    "audio/",
    "video/",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream"
}


def sanitize_filename(filename: str) -> str:
    """Strip dangerous characters and directory traversals from filenames."""
    filename = os.path.basename(filename)
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    if not filename:
        filename = "upload_file"
    return filename


def validate_file_extension(filename: str) -> str:
    """Validate and return normalized lowercase extension."""
    parts = filename.rsplit(".", 1)
    if len(parts) < 2:
        raise ValueError("File has no extension")
    ext = parts[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File extension '.{ext}' is not supported. Allowed: {sorted(list(ALLOWED_EXTENSIONS))}")
    return ext


def determine_modality(ext: str) -> str:
    """Map extension to system modality."""
    if ext in {"pdf", "docx", "doc", "txt", "md"}:
        return "document"
    elif ext in {"png", "jpg", "jpeg", "webp", "bmp"}:
        return "image"
    elif ext in {"mp3", "wav", "m4a", "ogg", "webm"}:
        return "audio"
    elif ext in {"mp4", "mov", "avi", "mkv"}:
        return "video"
    elif ext in {"csv", "xlsx", "xls"}:
        return "dataset"
    return "document"
