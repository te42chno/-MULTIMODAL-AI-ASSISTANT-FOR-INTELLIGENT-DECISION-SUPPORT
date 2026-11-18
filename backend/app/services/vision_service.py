import os
import base64
import logging
import mimetypes
from typing import Dict, Any, List, Optional

import httpx
from PIL import Image

from app.config import settings
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)

_DEFAULT_PALETTE = ["#1e293b", "#3b82f6", "#8b5cf6"]

# OpenCV (~112 MB) and scikit-learn are excluded from the Vercel function.
# Locally the original OpenCV + K-means + Tesseract path is used unchanged.
try:
    import cv2
    import numpy as np

    _CV2_AVAILABLE = True
except ImportError:  # Vercel serverless runtime
    cv2 = None
    np = None
    _CV2_AVAILABLE = False


class VisionService:
    """Vision and OCR service with a lightweight Pillow fallback for serverless."""

    def __init__(self):
        self.provider = settings.VISION_PROVIDER.lower()
        self.model = settings.VISION_MODEL
        self.api_key = (settings.VISION_API_KEY or settings.LLM_API_KEY).strip()

    async def analyze_image(self, image_path: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """Analyse an image: dimensions, palette, OCR and optional VLM caption."""
        image_path = storage_service.resolve(image_path)
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                img_format = img.format or "JPEG"
                mode = img.mode
                rgb = img.convert("RGB")

                if _CV2_AVAILABLE:
                    cv_img = cv2.imread(image_path)
                    palette = self._extract_dominant_colors_cv(cv_img)
                    ocr_text = self._extract_ocr_text_cv(cv_img)
                else:
                    palette = self._extract_dominant_colors_pil(rgb)
                    ocr_text = self._extract_ocr_text_pil(rgb)
        except Exception as e:
            logger.error("Error analyzing image %s: %s", image_path, e)
            raise ValueError(f"Failed to process image: {str(e)}")

        description = ""
        try:
            if self.provider == "gemini" and self.api_key:
                description = await self._call_gemini_vision(image_path, prompt)
            elif self.provider == "openai" and self.api_key:
                description = await self._call_openai_vision(image_path, prompt)
        except Exception as exc:
            logger.warning("VLM request failed (%s); using local visual summary.", exc)
            description = ""

        if not description:
            engine = "OpenCV & Tesseract OCR" if _CV2_AVAILABLE else "Pillow"
            description = self._generate_visual_heuristics(
                width, height, img_format, palette, ocr_text, prompt, engine
            )

        return {
            "width": width,
            "height": height,
            "format": img_format,
            "description": description,
            "extracted_text": ocr_text or None,
            "color_palette": palette,
            "key_features": [
                f"Dimensions: {width}x{height}px",
                f"Aspect Ratio: {round(width / max(height, 1), 2)}",
                f"Color Channels: {mode}",
                "Text Elements Detected: "
                + (f"Yes ({len(ocr_text.split())} words)" if ocr_text else "None"),
            ],
        }

    # ---- original local path -------------------------------------------------
    @staticmethod
    def _extract_dominant_colors_cv(cv_img) -> List[str]:
        if cv_img is None:
            return ["#000000"]
        try:
            resized = cv2.resize(cv_img, (50, 50), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            pixels = rgb.reshape(-1, 3)
            from sklearn.cluster import MiniBatchKMeans

            kmeans = MiniBatchKMeans(n_clusters=3, random_state=42, n_init="auto")
            kmeans.fit(pixels)
            hex_colors = []
            for center in kmeans.cluster_centers_:
                r, g, b = [int(c) for c in center]
                hex_colors.append(f"#{r:02x}{g:02x}{b:02x}")
            return hex_colors
        except Exception:
            return _DEFAULT_PALETTE

    @staticmethod
    def _extract_ocr_text_cv(cv_img) -> str:
        if cv_img is None:
            return ""
        try:
            import pytesseract

            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
            return pytesseract.image_to_string(thresh).strip()
        except Exception:
            return ""

    # ---- serverless fallback path -------------------------------------------
    @staticmethod
    def _extract_dominant_colors_pil(rgb_image: Image.Image) -> List[str]:
        try:
            thumb = rgb_image.copy()
            thumb.thumbnail((48, 48))
            counts = thumb.getcolors(maxcolors=4096)
            if not counts:
                return _DEFAULT_PALETTE
            counts.sort(reverse=True)
            return ["#%02x%02x%02x" % color for _, color in counts[:3]]
        except Exception:
            return _DEFAULT_PALETTE

    @staticmethod
    def _extract_ocr_text_pil(rgb_image: Image.Image) -> str:
        try:
            import pytesseract

            return (pytesseract.image_to_string(rgb_image) or "").strip()
        except Exception:
            return ""

    # ---- VLM providers -------------------------------------------------------
    async def _call_gemini_vision(self, image_path: str, prompt: Optional[str]) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {"x-goog-api-key": self.api_key}
        with open(image_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")

        mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
        user_prompt = prompt or (
            "Describe this clinical or scientific image precisely. Report visible findings, "
            "charts, labels or text. State uncertainty where present. Academic demonstration only."
        )
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": user_prompt},
                        {"inlineData": {"mimeType": mime_type, "data": b64_img}},
                    ],
                }
            ]
        }
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _call_openai_vision(self, image_path: str, prompt: Optional[str]) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        with open(image_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        user_prompt = prompt or (
            "Analyze this image and describe its key elements, visible structure, and relevant details."
        )
        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                    ],
                }
            ],
            "max_tokens": 1000,
        }
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _generate_visual_heuristics(
        width: int,
        height: int,
        fmt: str,
        palette: List[str],
        ocr_text: str,
        user_prompt: Optional[str],
        engine: str = "OpenCV & Tesseract OCR",
    ) -> str:
        aspect = "landscape" if width > height else ("portrait" if height > width else "square")
        text_info = f'Visible text extracted:\n"{ocr_text}"' if ocr_text else "No machine-readable text was detected in the image."
        return (
            f"**Visual Assessment Summary**\n\n"
            f"- **Resolution:** {width}x{height} pixels ({aspect} orientation, format: {fmt})\n"
            f"- **Dominant Color Palette:** {', '.join(palette)}\n"
            f"- **OCR Text Analysis:** {text_info}\n\n"
            f"*(Provider Mode: Local Vision Engine with {engine}. Connect Gemini or OpenAI API key for generative semantic scene captioning.)*"
        )


# Global singleton
vision_service = VisionService()
