"""
LLM Service: handles communication with Gemini API.

Uses the OpenAI-compatible SDK with Gemini's base URL.
Extracts Python code from LLM responses for execution in the sandbox.
"""

from __future__ import annotations

import os
import re
from typing import Optional

from openai import OpenAI

# ─── Gemini ───────────────────────────────────────────────────────
API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_MODEL = "models/gemini-2.5-flash"


class LLMService:
    """Handles LLM interactions via Gemini API (OpenAI-compatible)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        """Lazy-init the OpenAI client pointing to Gemini."""
        if self._client is None:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=API_BASE_URL,
            )
        return self._client

    @property
    def is_configured(self) -> bool:
        """Check if API key is set."""
        return bool(self.api_key) and "your-" not in self.api_key

    @property
    def provider_info(self) -> str:
        return f"Gemini ({self.model})"

    # ─── Core API call ──────────────────────────────────────────────

    def ask(self, context: str) -> str:
        """Send a prompt and return the raw response text."""
        if not self.is_configured:
            raise RuntimeError(
                "API key de Gemini no configurada. "
                "Andá a Settings y cargá tu API key de https://aistudio.google.com/apikey"
            )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Sos un experto en análisis de datos con Python. "
                            "Siempre respondés en español argentino (voseo)."
                        ),
                    },
                    {
                        "role": "user",
                        "content": context,
                    },
                ],
                temperature=0.1,
                max_tokens=8192,
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            error_str = str(e).lower()

            if "rate limit" in error_str or "429" in error_str:
                raise ConnectionError(
                    "Límite de tasa de Gemini alcanzado. "
                    "Esperá unos segundos e intentá de nuevo."
                )
            elif "api key" in error_str or "authentication" in error_str or "401" in error_str:
                raise RuntimeError(
                    "API key de Gemini inválida. Verificá tu key en https://aistudio.google.com/apikey"
                )
            elif "quota" in error_str or "403" in error_str:
                raise ConnectionError(
                    "Cuota de Gemini agotada. Esperá al próximo período."
                )
            elif "timeout" in error_str or "timed out" in error_str:
                raise ConnectionError(
                    "Conexión con Gemini timed out. Verificá tu internet."
                )
            elif "model_not_found" in error_str or "not found" in error_str:
                raise RuntimeError(
                    f"Modelo '{self.model}' no encontrado. Verificá el nombre."
                )
            else:
                raise ConnectionError(f"Error al conectar con Gemini: {e}")

    # ─── Code Extraction ────────────────────────────────────────────

    @staticmethod
    def extract_code(response: str) -> Optional[str]:
        """Extract Python code from an LLM response."""
        pattern = r"```(?:python|py)\s*\n?(.*?)```"
        match = re.search(pattern, response, re.DOTALL)
        if match:
            code = match.group(1).strip()
            if code:
                return code

        pattern2 = r"```\s*\n?(.*?)```"
        match2 = re.search(pattern2, response, re.DOTALL)
        if match2:
            code = match2.group(1).strip()
            if code:
                return code

        return None

    @staticmethod
    def extract_text(response: str) -> str:
        """Extract non-code text from an LLM response."""
        text = re.sub(r"```(?:python|py)?\s*\n?.*?```", "", response, flags=re.DOTALL)
        text = re.sub(r"`[^`]+`", "", text)
        return text.strip()

    # ─── High-level API ─────────────────────────────────────────────

    def generate_code(self, context: str) -> tuple[str, str, str]:
        """Send context, get back code + text."""
        raw = self.ask(context)
        code = self.extract_code(raw) or ""
        text = self.extract_text(raw)

        if not code and not text:
            text = raw

        return code, text, raw
