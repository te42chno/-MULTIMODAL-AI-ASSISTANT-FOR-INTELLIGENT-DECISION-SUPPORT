from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.audio import AudioTranscriptionResponse, AudioSynthesisRequest, AudioSynthesisResponse
from app.repositories.file_repo import FileRepository
from app.services.speech_service import speech_service

router = APIRouter()


@router.post("/transcribe", response_model=AudioTranscriptionResponse)
async def transcribe_audio_endpoint(file_id: str = Body(..., embed=True), db: Session = Depends(get_db)):
    """Transcribe an uploaded audio file."""
    file_repo = FileRepository(db)
    file_rec = file_repo.get_file(file_id)
    if not file_rec:
        raise HTTPException(status_code=404, detail="Audio file not found.")

    try:
        res = speech_service.transcribe_audio(file_rec.file_path)
        return AudioTranscriptionResponse(
            file_id=file_rec.id,
            filename=file_rec.filename,
            duration_seconds=res.get("duration_seconds"),
            transcription=res.get("transcription", ""),
            language="en",
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/synthesize", response_model=AudioSynthesisResponse)
async def synthesize_speech_endpoint(request: AudioSynthesisRequest):
    """Text-to-speech endpoint (returns status for browser Web Speech API or backend player)."""
    return AudioSynthesisResponse(
        format="mp3",
        message=f"Ready to synthesize {len(request.text.split())} words using browser Web Speech synthesis."
    )
