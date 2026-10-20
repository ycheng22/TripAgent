from __future__ import annotations

from typing import Literal

from app.settings import Settings
from providers.base import LLMProvider
from providers.openai_compatible import OpenAICompatibleProvider

ProviderTier = Literal["low_cost", "western_hosted"]

def create_provider(
    tier: ProviderTier = "low_cost",
    settings: Settings | None = None,
    specific_provider: str | None = None,
) -> LLMProvider:
    """
    Tier-based provider factory honoring AGENTS.md Section 1.3.
    - 'low_cost' (default for offline evals): routes to DeepSeek-V4.1-Flash (API model 'deepseek-flash')
    - 'western_hosted' (for user-facing): routes to GPT-4o-mini
    """
    if settings is None:
        from app.settings import settings as default_settings
        settings = default_settings

    # Explicit override if requested (e.g., comparing deepseek vs openai in evals)
    target = specific_provider or ("deepseek" if tier == "low_cost" else "openai")

    if target == "deepseek":
        api_key = settings.deepseek_api_key or ""
        return OpenAICompatibleProvider(
            api_key=api_key,
            base_url=settings.deepseek_base_url,
            model="deepseek-flash",
            provider_name="deepseek",
        )
    elif target == "openai":
        api_key = settings.openai_api_key or ""
        return OpenAICompatibleProvider(
            api_key=api_key,
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
            provider_name="openai",
        )
    else:
        raise ValueError(f"Unknown provider target: {target}")
