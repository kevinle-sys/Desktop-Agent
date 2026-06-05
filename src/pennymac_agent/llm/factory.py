"""Factory that builds the configured LLM provider."""

from __future__ import annotations

from typing import Optional

from ..config.settings import Settings, get_settings
from .base import LLMProvider


def build_provider(settings: Optional[Settings] = None) -> LLMProvider:
    """Instantiate the provider selected by ``settings.llm_provider``.

    Raises:
        ValueError: if the selected provider has no API key configured.
    """
    settings = settings or get_settings()

    if not settings.active_api_key:
        raise ValueError(
            f"LLM_PROVIDER='{settings.llm_provider}' is selected but its API "
            f"key is not set. Add the key to your .env file."
        )

    common = {
        "model": settings.active_model,
        "max_tokens": settings.llm_max_tokens,
        "temperature": settings.llm_temperature,
    }

    if settings.llm_provider == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(api_key=settings.active_api_key, **common)

    if settings.llm_provider == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=settings.active_api_key, **common)

    raise ValueError(f"Unknown LLM provider: {settings.llm_provider!r}")
