import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.decision import DecisionSupportRequest, DecisionSupportResponse
from app.services.decision_support_service import DecisionSupportService
from app.models.db_models import DecisionReport
import json

router = APIRouter()


@router.post("", response_model=DecisionSupportResponse)
async def generate_decision_report_endpoint(request: DecisionSupportRequest, db: Session = Depends(get_db)):
    """Generate a multi-criteria decision intelligence report based on multimodal evidence."""
    try:
        service = DecisionSupportService(db)
        report_schema = await service.generate_decision_report(
            query=request.query,
            conversation_id=request.conversation_id,
            file_ids=request.file_ids,
            criteria=request.criteria
        )

        conv_id = request.conversation_id or str(uuid.uuid4())
        
        # Save decision report to DB
        db_report = DecisionReport(
            id=str(uuid.uuid4()),
            conversation_id=conv_id,
            title=report_schema.title,
            objective=report_schema.objective,
            report_json=json.dumps(report_schema.model_dump())
        )
        db.add(db_report)
        db.commit()

        return DecisionSupportResponse(
            report_id=db_report.id,
            conversation_id=conv_id,
            report=report_schema
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
