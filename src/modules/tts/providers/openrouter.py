"""OpenRouter OpenAI-compatible /audio/speech TTS."""

from __future__ import annotations

import logging

import httpx

from src.modules.llm.providers.openai_compat import OPENROUTER_BASE_URL

logger = logging.getLogger(__name__)


class OpenRouterTts:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        model: str,
        voice: str,
        response_format: str = "mp3",
    ) -> None:
        self._api_key = api_key
        self._base_url = (base_url or OPENROUTER_BASE_URL).rstrip("/")
        self._model = model
        self._voice = voice
        self._response_format = response_format
        self.last_generation_id: str | None = None
        self.last_content_type: str = (
            "audio/mpeg" if response_format == "mp3" else "audio/pcm"
        )

    async def synthesize(self, text: str) -> bytes | None:
        if not (text or "").strip():
            return None
        url = f"{self._base_url}/audio/speech"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "input": text,
                    "voice": self._voice,
                    "response_format": self._response_format,
                },
            )
            response.raise_for_status()
        self.last_generation_id = response.headers.get("X-Generation-Id")
        content_type = response.headers.get("Content-Type")
        if content_type:
            self.last_content_type = content_type.split(";")[0].strip()
        audio = response.content
        if not audio:
            logger.warning("OpenRouter TTS returned empty body")
            return None
        return audio
