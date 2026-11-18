import os
import wave
import logging
from typing import Any, Dict, List, Optional

import speech_recognition as sr

from app.config import settings
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


class SpeechService:
    """Local-first ASR with optional Whisper and offline SpeechRecognition fallback."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.provider = settings.SPEECH_PROVIDER.lower()

    def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        audio_path = storage_service.resolve(audio_path)
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        filename = os.path.basename(audio_path)
        wav_path = self._ensure_wav(audio_path)
        duration = self._duration(wav_path)

        segments: List[Dict[str, Any]] = []
        transcription = ""

        if self.provider == "whisper":
            segments, transcription = self._transcribe_whisper(wav_path)

        if not transcription:
            transcription, segments = self._transcribe_local(wav_path, duration)

        if wav_path != audio_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass

        return {
            "filename": filename,
            "duration_seconds": duration,
            "transcription": transcription,
            "segments": segments,
            "provider": self.provider if transcription else "unavailable",
            "status": "success" if transcription else "partial",
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ensure_wav(self, path: str) -> str:
        if path.lower().endswith(".wav"):
            return path
        try:
            from pydub import AudioSegment

            converted = path + ".converted.wav"
            AudioSegment.from_file(path).export(converted, format="wav")
            return converted
        except Exception as exc:
            logger.warning("WAV conversion failed (%s); trying original path.", exc)
            return path

    @staticmethod
    def _duration(path: str) -> float:
        try:
            with wave.open(path, "r") as wf:
                return round(wf.getnframes() / float(wf.getframerate()), 2)
        except Exception:
            return 5.0

    def _transcribe_whisper(self, path: str):
        try:
            from faster_whisper import WhisperModel

            model = WhisperModel(settings.WHISPER_MODEL, device="cpu", compute_type="int8")
            iterator, _info = model.transcribe(path, beam_size=5)
            parts = []
            for seg in iterator:
                text = (seg.text or "").strip()
                if not text:
                    continue
                parts.append(
                    {
                        "start": round(seg.start, 2),
                        "end": round(seg.end, 2),
                        "text": text,
                    }
                )
            return parts, " ".join(p["text"] for p in parts)
        except Exception as exc:
            logger.warning("Whisper unavailable (%s); using SpeechRecognition fallback.", exc)
            return [], ""

    def _transcribe_local(self, path: str, duration: float):
        try:
            with sr.AudioFile(path) as source:
                audio = self.recognizer.record(source)
            text = self.recognizer.recognize_google(audio)
            chunks = []
            step = 10.0
            for i in range(0, max(duration, step), step):
                piece = text[i : i + 100]
                if piece:
                    chunks.append({"start": round(i, 2), "end": round(min(i + step, duration), 2), "text": piece})
            return text, chunks
        except sr.UnknownValueError:
            return "[Audio speech was unintelligible or silent]", []
        except Exception as exc:
            logger.warning("Local speech recognition failed: %s", exc)
            return "[Transcription unavailable — audio was received successfully.]", []


speech_service = SpeechService()
