import os
import logging
from typing import Dict, Any

from app.config import settings
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)

# OpenCV is ~112 MB installed and is intentionally excluded from the Vercel
# function bundle. Local development still uses the exact original code path.
try:
    import cv2
except ImportError:  # Vercel serverless runtime
    cv2 = None


class VideoService:
    """Video processing service with frame extraction at intervals and timestamped summaries."""

    def __init__(self, frame_interval_seconds: int = None):
        self.frame_interval_seconds = (
            settings.VIDEO_FRAME_INTERVAL_SECONDS
            if frame_interval_seconds is None
            else frame_interval_seconds
        )

    @staticmethod
    def _serverless_fallback(filename: str) -> Dict[str, Any]:
        """Honest metadata-only result when OpenCV is not bundled in the runtime."""
        return {
            "filename": filename,
            "duration_seconds": 0.0,
            "fps": 0.0,
            "resolution": "unknown",
            "frame_count": 0,
            "extracted_frames": [],
            "overall_summary": (
                f"Video '{filename}' was received and stored, but interval frame extraction "
                "is unavailable in this serverless environment (OpenCV is not bundled). "
                "No visual timeline evidence was produced."
            ),
            "timeline_events": [
                {
                    "time": "00:00",
                    "seconds": 0.0,
                    "event": "Video received; frame extraction unavailable in serverless environment.",
                }
            ],
            "status": "partial",
        }

    def process_video(self, video_path: str, filename: str) -> Dict[str, Any]:
        """Extract key frames at intervals and compute timeline metadata."""
        video_path = storage_service.resolve(video_path)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if cv2 is None:
            logger.warning("OpenCV unavailable; returning metadata-only video result.")
            return self._serverless_fallback(filename)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("Could not open video file.")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_seconds = round(total_frames / fps, 2)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Enforce duration limit
        if duration_seconds > settings.MAX_VIDEO_DURATION_SECONDS:
            cap.release()
            raise ValueError(
                f"Video duration ({duration_seconds}s) exceeds maximum allowed limit ({settings.MAX_VIDEO_DURATION_SECONDS}s)."
            )

        frames_dir = os.path.join(os.path.dirname(video_path), f"frames_{os.path.splitext(filename)[0]}")
        os.makedirs(frames_dir, exist_ok=True)

        extracted_frames = []
        timeline_events = []
        frame_step = max(int(fps * self.frame_interval_seconds), 1)

        current_frame = 0
        extracted_count = 0

        while current_frame < total_frames and extracted_count < 15:  # limit to max 15 keyframes
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            timestamp = round(current_frame / fps, 1)
            mins = int(timestamp // 60)
            secs = int(timestamp % 60)
            formatted_time = f"{mins:02d}:{secs:02d}"

            frame_filename = f"frame_{extracted_count:03d}_{formatted_time.replace(':', '_')}.jpg"
            frame_path = os.path.join(frames_dir, frame_filename)
            cv2.imwrite(frame_path, frame)

            # Analyze frame basic visual properties
            mean_brightness = float(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean())
            brightness_label = "Bright" if mean_brightness > 130 else ("Dim" if mean_brightness < 70 else "Balanced")

            scene_desc = f"Keyframe at {formatted_time} ({brightness_label} lighting, {width}x{height})"

            extracted_frames.append({
                "timestamp_seconds": timestamp,
                "timestamp_formatted": formatted_time,
                "frame_index": current_frame,
                "image_path": frame_path,
                "scene_description": scene_desc,
                "key_entities": [brightness_label, f"Frame #{current_frame}"]
            })

            timeline_events.append({
                "time": formatted_time,
                "seconds": timestamp,
                "event": f"Scene progression at {formatted_time} - {brightness_label} illumination"
            })

            extracted_count += 1
            current_frame += frame_step

        cap.release()

        summary = (
            f"Video Analysis for '{filename}': Total duration {duration_seconds}s at {round(fps, 1)} FPS "
            f"({width}x{height} resolution). Successfully extracted {len(extracted_frames)} interval frames "
            f"spanning from 00:00 to {timeline_events[-1]['time'] if timeline_events else '00:00'}."
        )

        return {
            "filename": filename,
            "duration_seconds": duration_seconds,
            "fps": fps,
            "resolution": f"{width}x{height}",
            "frame_count": total_frames,
            "extracted_frames": extracted_frames,
            "overall_summary": summary,
            "timeline_events": timeline_events,
            "status": "success"
        }


# Global singleton
video_service = VideoService()
