from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ImageAnalysisRequest(BaseModel):
    file_id: str
    prompt: Optional[str] = "Describe this image and extract any key details or text."


class DetectedObject(BaseModel):
    label: str
    confidence: float
    box: Optional[List[int]] = None


class ImageAnalysisResponse(BaseModel):
    file_id: str
    filename: str
    width: int
    height: int
    format: str
    description: str
    extracted_text: Optional[str] = None
    color_palette: List[str] = Field(default_factory=list)
    key_features: List[str] = Field(default_factory=list)
    status: str = "success"
