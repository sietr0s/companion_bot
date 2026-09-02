from src.core.config import settings
from src.modules.llm.providers.openai_compat import OPENROUTER_BASE_URL
from src.modules.tts.providers.base import TtsProvider
from src.modules.tts.providers.stub import StubTts


def get_tts_provider() -> TtsProvider:
    return build_tts_provider()


def build_tts_provider() -> TtsProvider:
    name = (settings.TTS_PROVIDER or "stub").strip().lower()
    if name == "stub":
        return StubTts()
    if name in {"openrouter", "openai", "openai_compat"}:
        api_key = (settings.LLM_API_KEY or "").strip()
        if not api_key:
            raise RuntimeError(f"TTS_PROVIDER={name} требует LLM_API_KEY")
        base_url = (settings.LLM_BASE_URL or "").strip() or OPENROUTER_BASE_URL
        from src.modules.tts.providers.openrouter import OpenRouterTts

        return OpenRouterTts(
            api_key,
            base_url=base_url,
            model=settings.TTS_MODEL,
            voice=settings.TTS_VOICE,
            response_format=settings.TTS_RESPONSE_FORMAT,
        )
    raise ValueError(f"Unsupported TTS_PROVIDER: {settings.TTS_PROVIDER}")
