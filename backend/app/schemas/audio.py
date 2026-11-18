from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class AudioTranscriptionResponse(BaseModel):
    file_id: str
    filename: str
    duration_seconds: Optional[float] = None
    transcription: str
    language: Optional[str] = "en"
    confidence: Optional[float] = None
    status: str = "success"


class AudioSynthesisRequest(BaseModel):
    text: str
    voice: Optional[str] = "default"
    speed: Optional[float] = 1.0


class AudioSynthesisResponse(BaseModel):
    audio_base64: Optional[str] = None
    audio_url: Optional[str] = None
    format: str = "mp3"
    message: str = "Text synthesized successfully"
