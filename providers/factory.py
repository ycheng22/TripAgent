from __future__ import annotations

from typing import Literal, TypeVar

from pydantic import BaseModel

from app.settings import Settings
from core.telemetry import trace_genai_span
from providers.base import LLMProvider
from providers.openai_compatible import OpenAICompatibleProvider

ProviderTier = Literal["low_cost", "western_hosted"]
T = TypeVar("T", bound=BaseModel)


class FailoverProvider:
    """Wraps a primary provider with an automatic fallback provider (AGENTS.md Section 1.3)."""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.provider_name = primary.provider_name
        self.model = primary.model

    async def agenerate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        purpose: str,
        temperature: float = 0.2,
    ) -> tuple[T, int, int, float]:
        try:
            return await self.primary.agenerate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=response_model,
                purpose=purpose,
                temperature=temperature,
            )
        except Exception:  # noqa: BLE001
            with trace_genai_span(
                name="provider_failover",
                purpose=f"{purpose}_failover",
                model=self.fallback.model,
                provider=self.fallback.provider_name,
            ):
                return await self.fallback.agenerate_structured(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_model=response_model,
                    purpose=purpose,
                    temperature=temperature,
                )


def create_provider(
    tier: ProviderTier = "low_cost",
    settings: Settings | None = None,
    specific_provider: str | None = None,
) -> LLMProvider:
    """
    Tier-based provider factory honoring AGENTS.md Section 1.3.
    - 'low_cost' (offline evals): routes to DeepSeek-V4.1-Flash (API model 'deepseek-flash')
    - 'western_hosted' (user-facing generation): routes to Gemini 3.5 Flash Lite with failover
    """
    if settings is None:
        from app.settings import settings as default_settings

        settings = default_settings

    if specific_provider:
        target = specific_provider
    elif tier == "low_cost":
        target = "deepseek"
    elif settings.gemini_api_key:
        target = "gemini"
    elif settings.openai_api_key:
        target = "openai"
    else:
        target = "deepseek"

    if target == "gemini":
        gemini_provider = OpenAICompatibleProvider(
            api_key=settings.gemini_api_key or "placeholder",
            base_url=settings.gemini_base_url,
            model=settings.default_ai_model,
            provider_name="gemini",
        )
        # Configure failover to gpt-4o-mini if Gemini quota/credits are exhausted
        if settings.openai_api_key:
            fallback = OpenAICompatibleProvider(
                api_key=settings.openai_api_key,
                base_url="https://api.openai.com/v1",
                model="gpt-4o-mini",
                provider_name="openai",
            )
            return FailoverProvider(gemini_provider, fallback)
        elif settings.deepseek_api_key:
            fallback = OpenAICompatibleProvider(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                model="deepseek-flash",
                provider_name="deepseek",
            )
            return FailoverProvider(gemini_provider, fallback)
        return gemini_provider

    elif target == "deepseek":
        return OpenAICompatibleProvider(
            api_key=settings.deepseek_api_key or "placeholder",
            base_url=settings.deepseek_base_url,
            model="deepseek-flash",
            provider_name="deepseek",
        )
    elif target == "openai":
        return OpenAICompatibleProvider(
            api_key=settings.openai_api_key or "placeholder",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
            provider_name="openai",
        )
    else:
        raise ValueError(f"Unknown provider target: {target}")
