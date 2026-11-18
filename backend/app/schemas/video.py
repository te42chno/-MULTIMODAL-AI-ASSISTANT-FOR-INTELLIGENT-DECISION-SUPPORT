from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class VideoFrameInfo(BaseModel):
    timestamp_seconds: float
    timestamp_formatted: str
    frame_index: int
    image_path: str
    scene_description: str
    key_entities: List[str] = Field(default_factory=list)


class VideoAnalysisResponse(BaseModel):
    file_id: str
    filename: str
    duration_seconds: float
    fps: float
    resolution: str
    frame_count: int
    extracted_frames: List[VideoFrameInfo] = Field(default_factory=list)
    overall_summary: str
    timeline_events: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "success"
