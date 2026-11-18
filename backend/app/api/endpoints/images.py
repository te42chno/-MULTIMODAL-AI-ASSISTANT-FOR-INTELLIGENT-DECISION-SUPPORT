from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.image import ImageAnalysisRequest, ImageAnalysisResponse
from app.repositories.file_repo import FileRepository
from app.services.vision_service import vision_service

router = APIRouter()


@router.post("/analyze", response_model=ImageAnalysisResponse)
async def analyze_image_endpoint(request: ImageAnalysisRequest, db: Session = Depends(get_db)):
    """Analyze an uploaded image with vision and OCR."""
    file_repo = FileRepository(db)
    file_record = file_repo.get_file(request.file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="Image file not found.")

    try:
        analysis = await vision_service.analyze_image(file_record.file_path, request.prompt)
        return ImageAnalysisResponse(
            file_id=file_record.id,
            filename=file_record.filename,
            width=analysis["width"],
            height=analysis["height"],
            format=analysis["format"],
            description=analysis["description"],
            extracted_text=analysis.get("extracted_text"),
            color_palette=analysis.get("color_palette", []),
            key_features=analysis.get("key_features", []),
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
