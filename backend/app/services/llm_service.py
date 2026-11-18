import json
import logging
import re
from typing import Any, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM = (
    "You are MedReason, an academic clinical decision-support assistant. "
    "Answer ONLY from the supplied evidence. If the evidence is insufficient, say so explicitly. "
    "Cite evidence inline using its bracket ID, e.g. [E1]. Never invent medical facts. "
    "Always include: 'Academic demonstration only — not for clinical use.'"
)


class LLMService:
    """Provider adapter with grounded prompting and structured JSON output support."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.model = settings.LLM_MODEL
        self.api_key = settings.LLM_API_KEY.strip()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[str] = None,
        temperature: float = 0.25,
    ) -> str:
        system = system_instruction or DEFAULT_SYSTEM
        if context:
            system = f"{system}\n\n--- RETRIEVED EVIDENCE ---\n{context}\n--- END EVIDENCE ---"

        if self.provider == "gemini" and self.api_key:
            result = await self._call_gemini(prompt, system, temperature)
            if result:
                return result
        elif self.provider in {"groq", "openai"} and self.api_key:
            result = await self._call_openai_compatible(prompt, system, temperature)
            if result:
                return result
        elif self.provider == "ollama":
            result = await self._call_ollama(prompt, system, temperature)
            if result:
                return result

        return self._generate_grounded_mock(prompt, context)

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Ask the provider for a strict JSON object and parse it safely."""
        instruction = (
            (system_instruction or DEFAULT_SYSTEM)
            + "\n\nReturn ONLY a valid JSON object. No markdown, no commentary, no code fences."
        )
        raw = await self.generate_response(prompt, instruction, context, temperature=0.1)
        parsed = self._extract_json(raw)
        if parsed is None:
            logger.warning("Structured generation unavailable; using offline evidence inventory.")
        return parsed

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------
    async def _call_gemini(self, prompt: str, system: str, temperature: float) -> Optional[str]:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        headers = {"x-goog-api-key": self.api_key}
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": 2048},
        }
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:
            logger.warning("Gemini request failed: %s", exc)
            return None

    async def _call_openai_compatible(self, prompt: str, system: str, temperature: float) -> Optional[str]:
        base = "https://api.groq.com/openai/v1" if self.provider == "groq" else "https://api.openai.com/v1"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(f"{base}/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("%s request failed: %s", self.provider.upper(), exc)
            return None

    async def _call_ollama(self, prompt: str, system: str, temperature: float) -> Optional[str]:
        payload = {
            "model": self.model or "llama3",
            "prompt": f"{system}\n\nQuestion:\n{prompt}",
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post("http://localhost:11434/api/generate", json=payload)
                resp.raise_for_status()
                return resp.json().get("response")
        except Exception as exc:
            logger.warning("Ollama request failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Offline fallback
    # ------------------------------------------------------------------
    def _generate_grounded_mock(self, prompt: str, context: Optional[str]) -> str:
        if context and context.strip():
            lines = [line.strip() for line in context.splitlines() if line.strip() and not line.startswith("---")]
            bullets = "\n".join(f"- {line[:240]}" for line in lines[:5])
            return (
                f"### Offline retrieval preview\n\n{bullets}\n\n"
                f"**Assessment:** The retrieved context above is the only evidence available for "
                f"“{prompt.strip()}”. No provider synthesis or external facts were added.\n\n"
                "> Academic demonstration only — not for clinical use."
            )
        return (
            f"### MedReason clinical assistant\n\n"
            f"I received: *{prompt.strip()}*.\n\n"
            "Upload a clinical note, lab table, image, recording or video to build an evidence index. "
            "Then ask a question or enable Decision Support for a structured report.\n\n"
            "> Academic demonstration only — not for clinical use."
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_json(raw: str) -> Optional[Dict[str, Any]]:
        if not raw:
            return None
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            value = json.loads(cleaned[start : end + 1])
            return value if isinstance(value, dict) else None
        except Exception:
            return None


llm_service = LLMService()
