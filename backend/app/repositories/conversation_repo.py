import json
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.db_models import Conversation, Message


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_conversation(self, title: str = "New Conversation") -> Conversation:
        conv = Conversation(id=str(uuid.uuid4()), title=title)
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        return self.db.query(Conversation).filter(Conversation.id == conv_id).first()

    def list_conversations(self) -> List[Conversation]:
        return self.db.query(Conversation).order_by(Conversation.updated_at.desc()).all()

    def update_title(self, conv_id: str, title: str) -> Optional[Conversation]:
        conv = self.get_conversation(conv_id)
        if conv:
            conv.title = title
            conv.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(conv)
        return conv

    def delete_conversation(self, conv_id: str) -> bool:
        conv = self.get_conversation(conv_id)
        if conv:
            self.db.delete(conv)
            self.db.commit()
            return True
        return False

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        modality: str = "text",
        file_ids: Optional[List[str]] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
        metadata_json: Optional[Dict[str, Any]] = None
    ) -> Message:
        conv = self.get_conversation(conversation_id)
        if not conv:
            conv = self.create_conversation(title=content[:30] if role == "user" else "New Conversation")
            conversation_id = conv.id
        else:
            conv.updated_at = datetime.utcnow()

        msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            modality=modality,
            file_ids=json.dumps(file_ids or []),
            sources=json.dumps(sources or []),
            metadata_json=json.dumps(metadata_json or {})
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_messages(self, conversation_id: str) -> List[Message]:
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )
