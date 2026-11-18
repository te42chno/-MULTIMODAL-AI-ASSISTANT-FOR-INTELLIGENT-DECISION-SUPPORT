from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class Citation(BaseModel):
    source_id: str
    filename: str
    page_number: Optional[int] = None
    timestamp: Optional[str] = None
    row_or_item: Optional[str] = None
    snippet: str
    relevance_score: Optional[float] = None


class MessageItem(BaseModel):
    id: str
    conversation_id: str
    role: str  # user, assistant, system
    content: str
    modality: str = "text"
    file_ids: List[str] = Field(default_factory=list)
    sources: List[Citation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    modality: Optional[str] = "text"
    file_ids: Optional[List[str]] = Field(default_factory=list)
    is_decision_support: bool = False
    system_instruction: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    role: str = "assistant"
    content: str
    modality: str = "text"
    sources: List[Citation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
