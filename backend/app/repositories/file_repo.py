import json
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.db_models import FileRecord, DocumentChunk


class FileRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_file(
        self,
        filename: str,
        file_type: str,
        file_size: int,
        file_path: str,
        mime_type: Optional[str] = None,
        conversation_id: Optional[str] = None,
        summary: Optional[str] = None,
        metadata_dict: Optional[Dict[str, Any]] = None,
        status: str = "processed"
    ) -> FileRecord:
        record = FileRecord(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            filename=filename,
            file_type=file_type,
            mime_type=mime_type,
            file_size=file_size,
            file_path=file_path,
            summary=summary,
            metadata_json=json.dumps(metadata_dict or {}),
            status=status
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_file(self, file_id: str) -> Optional[FileRecord]:
        return self.db.query(FileRecord).filter(FileRecord.id == file_id).first()

    def list_files(self, conversation_id: Optional[str] = None) -> List[FileRecord]:
        query = self.db.query(FileRecord)
        if conversation_id:
            query = query.filter(FileRecord.conversation_id == conversation_id)
        return query.order_by(FileRecord.created_at.desc()).all()

    def update_file_summary(self, file_id: str, summary: str, metadata_dict: Optional[Dict[str, Any]] = None):
        record = self.get_file(file_id)
        if record:
            record.summary = summary
            if metadata_dict:
                existing = json.loads(record.metadata_json or "{}")
                existing.update(metadata_dict)
                record.metadata_json = json.dumps(existing)
            self.db.commit()
            self.db.refresh(record)
        return record

    def save_chunks(self, file_id: str, chunks_data: List[Dict[str, Any]]) -> List[DocumentChunk]:
        created_chunks = []
        for c in chunks_data:
            chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                file_id=file_id,
                chunk_index=c.get("chunk_index", 0),
                page_number=c.get("page_number"),
                text=c.get("text", ""),
                embedding_json=json.dumps(c.get("embedding", []))
            )
            self.db.add(chunk)
            created_chunks.append(chunk)
        self.db.commit()
        return created_chunks

    def get_chunks_by_file(self, file_id: str) -> List[DocumentChunk]:
        return (
            self.db.query(DocumentChunk)
            .filter(DocumentChunk.file_id == file_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )

    def get_all_chunks(self, file_ids: Optional[List[str]] = None) -> List[DocumentChunk]:
        query = self.db.query(DocumentChunk)
        if file_ids:
            query = query.filter(DocumentChunk.file_id.in_(file_ids))
        return query.all()
