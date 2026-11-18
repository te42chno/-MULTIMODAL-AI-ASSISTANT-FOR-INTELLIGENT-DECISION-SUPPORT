from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class DocumentUploadResponse(BaseModel):
    file_id: str
    filename: str
    file_size: int
    page_count: Optional[int] = None
    chunk_count: int
    summary: Optional[str] = None
    status: str = "processed"


class DocumentQueryRequest(BaseModel):
    query: str
    file_ids: Optional[List[str]] = None
    conversation_id: Optional[str] = None
    top_k: int = 4


class DocumentChunkResult(BaseModel):
    chunk_id: str
    file_id: str
    filename: str
    page_number: Optional[int] = None
    text: str
    score: float


class DocumentQueryResponse(BaseModel):
    answer: str
    sources: List[DocumentChunkResult]
    grounded: bool
