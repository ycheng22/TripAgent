from __future__ import annotations

import json
from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from core.telemetry import record_token_usage, trace_genai_span

T = TypeVar("T", bound=BaseModel)

class OpenAICompatibleProvider:
    """Universal provider for OpenAI and OpenAI-compatible endpoints (DeepSeek, Qwen)."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        provider_name: str,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.provider_name = provider_name
        self.client = AsyncOpenAI(api_key=api_key or "placeholder", base_url=base_url)

    def _get_client(self) -> AsyncOpenAI:
        # Check if chat completions create was mocked for unit tests
        chat_completions = getattr(getattr(self.client, "chat", None), "completions", None)
        create_fn = getattr(chat_completions, "create", None)
        if create_fn is not None and hasattr(create_fn, "assert_called"):
            return self.client
        return AsyncOpenAI(api_key=self.api_key or "placeholder", base_url=self.base_url)

    def _calculate_cost(self, tokens_in: int, tokens_out: int) -> float:
        model_lower = self.model.lower()
        if "gemini" in model_lower:
            # Gemini-3.5-flash-lite pricing ($0.075/1M input, $0.30/1M output)
            return (tokens_in * 0.075 + tokens_out * 0.30) / 1_000_000.0
        elif "deepseek" in model_lower:
            # DeepSeek-V4.1-Flash pricing ($0.14/1M input, $0.28/1M output)
            return (tokens_in * 0.14 + tokens_out * 0.28) / 1_000_000.0
        elif "gpt-4o-mini" in model_lower:
            # GPT-4o-mini pricing ($0.15/1M input, $0.60/1M output)
            return (tokens_in * 0.15 + tokens_out * 0.60) / 1_000_000.0
        elif "gpt-4o" in model_lower:
            # GPT-4o pricing ($2.50/1M input, $10.00/1M output)
            return (tokens_in * 2.50 + tokens_out * 10.00) / 1_000_000.0
        return (tokens_in * 0.15 + tokens_out * 0.60) / 1_000_000.0

    async def agenerate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        purpose: str,
        temperature: float = 0.2,
    ) -> tuple[T, int, int, float]:
        schema_json = json.dumps(response_model.model_json_schema())
        augmented_system_prompt = (
            f"{system_prompt}\n\n"
            f"You MUST output valid JSON conforming strictly to this JSON schema:\n"
            f"{schema_json}\n"
            f"Do not include any markdown formatting like ```json or ```. Return pure JSON only."
        )

        with trace_genai_span(
            name=f"chat_{self.model}",
            purpose=purpose,
            model=self.model,
            provider=self.provider_name,
        ) as span:
            client = self._get_client()
            try:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": augmented_system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
            finally:
                if client is not self.client:
                    await client.close()

            usage = response.usage
            tokens_in = usage.prompt_tokens if usage else 0
            tokens_out = usage.completion_tokens if usage else 0
            record_token_usage(span, tokens_in, tokens_out)

            cost_usd = self._calculate_cost(tokens_in, tokens_out)
            span.set_attribute("gen_ai.usage.cost_usd", cost_usd)

            content = response.choices[0].message.content or "{}"
            content_clean = content.strip()
            if content_clean.startswith("```"):
                lines = content_clean.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content_clean = "\n".join(lines).strip()
            parsed = response_model.model_validate_json(content_clean)
            return parsed, tokens_in, tokens_out, cost_usd
