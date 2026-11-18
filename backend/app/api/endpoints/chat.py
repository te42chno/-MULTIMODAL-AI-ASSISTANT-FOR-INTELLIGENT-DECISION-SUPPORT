from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.orchestrator import OrchestrationService

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def post_chat_message(request: ChatRequest, db: Session = Depends(get_db)):
    """Unified chat endpoint handling text, modality context, and decision support."""
    try:
        orchestrator = OrchestrationService(db)
        response = await orchestrator.handle_user_message(
            conversation_id=request.conversation_id,
            message=request.message,
            modality=request.modality or "text",
            file_ids=request.file_ids,
            is_decision_support=request.is_decision_support,
            system_instruction=request.system_instruction
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
