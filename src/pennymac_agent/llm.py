"""CrewAI LLM construction.

CrewAI talks to providers through LiteLLM, so the only provider-specific detail
we need is the model string and API key. This keeps the framework pluggable
between OpenAI and Anthropic via ``LLM_PROVIDER`` in ``.env``.
"""

from __future__ import annotations

from typing import Optional

from .config.settings import Settings, get_settings


def _litellm_model(provider: str, model: str) -> str:
    """Map a provider + bare model name to a LiteLLM-style model string."""
    if provider == "anthropic":
        # LiteLLM expects an "anthropic/<model>" prefix.
        return model if model.startswith("anthropic/") else f"anthropic/{model}"
    # OpenAI models are used bare (e.g. "gpt-4o").
    return model


def build_llm(settings: Optional[Settings] = None):
    """Build the CrewAI LLM for specialist agents from settings."""
    from crewai import LLM

    settings = settings or get_settings()
    return LLM(
        model=_litellm_model(settings.llm_provider, settings.active_model),
        api_key=settings.active_api_key,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )


def build_manager_llm(settings: Optional[Settings] = None):
    """Build the LLM that powers the hierarchical crew manager.

    Uses ``MANAGER_MODEL`` when set, otherwise the active provider model.
    """
    from crewai import LLM

    settings = settings or get_settings()
    model = settings.manager_model or settings.active_model
    return LLM(
        model=_litellm_model(settings.llm_provider, model),
        api_key=settings.active_api_key,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )
