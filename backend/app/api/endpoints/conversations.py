import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database import get_db
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.file_repo import FileRepository

router = APIRouter()


@router.get("")
def list_conversations_endpoint(db: Session = Depends(get_db)):
    """List all saved conversations sorted by recent activity."""
    repo = ConversationRepository(db)
    convs = repo.list_conversations()
    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
            "message_count": len(c.messages)
        }
        for c in convs
    ]


@router.get("/{conversation_id}")
def get_conversation_details_endpoint(conversation_id: str, db: Session = Depends(get_db)):
    """Retrieve full conversation message history."""
    repo = ConversationRepository(db)
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    messages = []
    for m in conv.messages:
        messages.append({
            "id": m.id,
            "conversation_id": m.conversation_id,
            "role": m.role,
            "content": m.content,
            "modality": m.modality,
            "file_ids": json.loads(m.file_ids or "[]"),
            "sources": json.loads(m.sources or "[]"),
            "metadata": json.loads(m.metadata_json or "{}"),
            "created_at": m.created_at.isoformat()
        })

    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
        "messages": messages
    }


@router.delete("/{conversation_id}")
def delete_conversation_endpoint(conversation_id: str, db: Session = Depends(get_db)):
    """Delete a conversation and its messages."""
    repo = ConversationRepository(db)
    success = repo.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"message": "Conversation deleted successfully."}


@router.get("/files/list")
def list_uploaded_files_endpoint(conversation_id: str = None, db: Session = Depends(get_db)):
    """List uploaded files across system or for a specific conversation."""
    file_repo = FileRepository(db)
    files = file_repo.list_files(conversation_id)
    return [
        {
            "id": f.id,
            "filename": f.filename,
            "file_type": f.file_type,
            "file_size": f.file_size,
            "summary": f.summary,
            "metadata": json.loads(f.metadata_json or "{}"),
            "created_at": f.created_at.isoformat()
        }
        for f in files
    ]
