import json
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.dataset import DatasetSummaryResponse, DatasetQueryRequest, DatasetQueryResponse
from app.repositories.file_repo import FileRepository
from app.services.data_analysis_service import data_analysis_service

router = APIRouter()


@router.post("/analyze", response_model=DatasetSummaryResponse)
async def analyze_dataset_endpoint(file_id: str = Body(..., embed=True), db: Session = Depends(get_db)):
    """Analyze a structured dataset and compute statistics and charts."""
    file_repo = FileRepository(db)
    file_rec = file_repo.get_file(file_id)
    if not file_rec:
        raise HTTPException(status_code=404, detail="Dataset file not found.")

    try:
        res = data_analysis_service.analyze_dataset(file_rec.file_path, file_rec.filename)
        return DatasetSummaryResponse(
            file_id=file_rec.id,
            filename=file_rec.filename,
            row_count=res["row_count"],
            column_count=res["column_count"],
            columns=res["columns"],
            missing_value_count=res["missing_value_count"],
            duplicate_row_count=res["duplicate_row_count"],
            preview_rows=res["preview_rows"],
            summary_statistics=res["summary_statistics"],
            recommended_charts=res["recommended_charts"],
            correlations=res.get("correlations")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=DatasetQueryResponse)
async def query_dataset_endpoint(request: DatasetQueryRequest, db: Session = Depends(get_db)):
    """Query dataset using safe deterministic Pandas planning without eval/exec."""
    file_repo = FileRepository(db)
    file_rec = file_repo.get_file(request.file_id)
    if not file_rec:
        raise HTTPException(status_code=404, detail="Dataset file not found.")

    try:
        res = data_analysis_service.answer_question(file_rec.file_path, file_rec.filename, request.question)
        return DatasetQueryResponse(
            file_id=file_rec.id,
            question=request.question,
            answer=res["answer"],
            calculation_summary=res["calculation_summary"],
            chart=res.get("chart"),
            data_table=res.get("data_table")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
