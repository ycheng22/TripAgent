from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from app.settings import Settings
from providers.factory import create_provider
from providers.openai_compatible import OpenAICompatibleProvider


class DummyPlan(BaseModel):
    title: str
    estimated_cost: float


def test_cost_calculation() -> None:
    provider_ds = OpenAICompatibleProvider(api_key="mock", base_url="mock", model="deepseek-chat", provider_name="deepseek")
    cost_ds = provider_ds._calculate_cost(tokens_in=1000, tokens_out=500)
    # 1000 * 0.14 / 1M + 500 * 0.28 / 1M = 0.00014 + 0.00014 = 0.00028
    assert round(cost_ds, 6) == 0.00028

    provider_oa = OpenAICompatibleProvider(api_key="mock", base_url="mock", model="gpt-4o-mini", provider_name="openai")
    cost_oa = provider_oa._calculate_cost(tokens_in=1000, tokens_out=500)
    # 1000 * 0.15 / 1M + 500 * 0.60 / 1M = 0.00015 + 0.00030 = 0.00045
    assert round(cost_oa, 6) == 0.00045


@pytest.mark.asyncio
async def test_provider_structured_output_mocked() -> None:
    provider = OpenAICompatibleProvider(api_key="mock", base_url="mock", model="deepseek-chat", provider_name="deepseek")

    mock_choice = MagicMock()
    mock_choice.message.content = '{"title": "Paris Weekend", "estimated_cost": 450.0}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 200
    mock_response.usage.completion_tokens = 50

    provider.client.chat.completions.create = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

    res, tokens_in, tokens_out, cost = await provider.agenerate_structured(
        system_prompt="system",
        user_prompt="user",
        response_model=DummyPlan,
        purpose="test_plan",
    )

    assert res.title == "Paris Weekend"
    assert res.estimated_cost == 450.0
    assert tokens_in == 200
    assert tokens_out == 50
    assert cost > 0


def test_factory_creates_providers() -> None:
    settings = Settings(
        allowed_origins=[],
        max_steps=25,
        max_tokens_per_task=60000,
        max_cost_per_task=0.05,
        max_replans=3,
        git_sha="sha",
        deepseek_api_key="ds-key",
        openai_api_key="oa-key",
    )

    ds = create_provider("low_cost", settings=settings)
    assert isinstance(ds, OpenAICompatibleProvider)
    assert ds.model == "deepseek-flash"
    assert ds.provider_name == "deepseek"

    oa = create_provider("western_hosted", settings=settings)
    assert isinstance(oa, OpenAICompatibleProvider)
    assert oa.model == "gpt-4o-mini"
    assert oa.provider_name == "openai"
