import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import backref, relationship
from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    decision_reports = relationship("DecisionReport", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    modality = Column(String(50), default="text")  # text, document, image, audio, video, dataset, decision
    file_ids = Column(Text, default="[]")  # JSON list of attached file IDs
    sources = Column(Text, default="[]")   # JSON list of citations
    metadata_json = Column(Text, default="{}")  # Additional context (charts, metrics, tokens)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class FileRecord(Base):
    __tablename__ = "files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), nullable=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # document, image, audio, video, dataset
    mime_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    metadata_json = Column(Text, default="{}")  # Extra stats, column list, duration, dimensions
    status = Column(String(50), default="processed")  # processing, processed, error
    created_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("DocumentChunk", back_populates="file", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String(36), ForeignKey("files.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    text = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=True)  # vector representation
    created_at = Column(DateTime, default=datetime.utcnow)

    file = relationship("FileRecord", back_populates="chunks")


class EvidenceChunk(Base):
    """Unified retrievable unit for every modality (document, table, image, audio, video)."""

    __tablename__ = "evidence_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String(36), ForeignKey("files.id"), nullable=False)
    chunk_index = Column(Integer, default=0)
    modality = Column(String(50), default="document")
    source_ref = Column(String(100), default="")  # page, row, timestamp or frame
    text = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=True)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    file = relationship(
        "FileRecord",
        backref=backref("evidence_chunks", cascade="all, delete-orphan"),
    )


class DecisionReport(Base):
    __tablename__ = "decision_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    title = Column(String(255), nullable=False)
    objective = Column(Text, nullable=False)
    report_json = Column(Text, nullable=False)  # Full structured schema
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="decision_reports")
