from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.video import VideoAnalysisResponse
from app.repositories.file_repo import FileRepository
from app.services.video_service import video_service

router = APIRouter()


@router.post("/analyze", response_model=VideoAnalysisResponse)
async def analyze_video_endpoint(file_id: str = Body(..., embed=True), db: Session = Depends(get_db)):
    """Trigger video frame interval extraction and timeline analysis."""
    file_repo = FileRepository(db)
    file_rec = file_repo.get_file(file_id)
    if not file_rec:
        raise HTTPException(status_code=404, detail="Video file not found.")

    try:
        res = video_service.process_video(file_rec.file_path, file_rec.filename)
        return VideoAnalysisResponse(
            file_id=file_rec.id,
            filename=file_rec.filename,
            duration_seconds=res["duration_seconds"],
            fps=res["fps"],
            resolution=res["resolution"],
            frame_count=res["frame_count"],
            extracted_frames=res["extracted_frames"],
            overall_summary=res["overall_summary"],
            timeline_events=res["timeline_events"],
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
