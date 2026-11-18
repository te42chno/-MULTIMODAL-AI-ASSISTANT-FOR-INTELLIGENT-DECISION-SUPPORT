"""Storage abstraction that works on both local disks and ephemeral serverless filesystems.

Local development keeps files on disk. Serverless deployments (Vercel, etc.) persist the
upload bytes in the database and materialise them into a temporary directory for the
duration of a single request, where the existing modality processors can read them.
"""

import logging
import re
import uuid
from pathlib import Path

from app.config import UPLOAD_DIR, settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)

_BLOB_PREFIX = "blob:"
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class StorageService:
    @property
    def backend(self) -> str:
        return settings.STORAGE_BACKEND

    def save(self, content: bytes, filename: str, subfolder: str) -> str:
        """Persist upload bytes and return an opaque path/key stored on FileRecord."""
        clean_name = _SAFE_NAME.sub("_", Path(filename or "uploaded_file").name)[:180] or "upload"

        if self.backend == "database":
            from app.models.db_models import StoredBlob

            db = SessionLocal()
            try:
                blob = StoredBlob(
                    id=str(uuid.uuid4()),
                    filename=clean_name,
                    content_type=None,
                    data=content,
                )
                db.add(blob)
                db.commit()
                return f"{_BLOB_PREFIX}{blob.id}"
            finally:
                db.close()

        dest_dir = UPLOAD_DIR / subfolder
        dest_dir.mkdir(parents=True, exist_ok=True)
        file_path = dest_dir / f"{uuid.uuid4().hex[:8]}_{clean_name}"
        file_path.write_bytes(content)
        return str(file_path)

    def resolve(self, path_or_key: str) -> str:
        """Return a readable local path for a stored upload, materialising blobs if needed."""
        if not path_or_key or not path_or_key.startswith(_BLOB_PREFIX):
            return path_or_key

        blob_id = path_or_key[len(_BLOB_PREFIX):]
        from app.models.db_models import StoredBlob

        temp_dir = Path(settings.TEMP_DIR)
        temp_dir.mkdir(parents=True, exist_ok=True)

        db = SessionLocal()
        try:
            blob = db.get(StoredBlob, blob_id)
            if blob is None:
                raise FileNotFoundError(f"Stored upload {blob_id} was not found")
            safe_name = _SAFE_NAME.sub("_", Path(blob.filename).name)[:180] or "upload"
            target = temp_dir / f"{blob_id}_{safe_name}"
            if not target.exists():
                target.write_bytes(blob.data)
            return str(target)
        finally:
            db.close()

    def delete(self, path_or_key: str) -> None:
        """Best-effort cleanup; blobs are intentionally retained for reproducibility."""
        if not path_or_key or path_or_key.startswith(_BLOB_PREFIX):
            return
        try:
            Path(path_or_key).unlink(missing_ok=True)
        except OSError as exc:
            logger.debug("Could not remove local upload: %s", exc)


storage_service = StorageService()
