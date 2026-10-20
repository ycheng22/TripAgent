from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class LLMProvider(Protocol):
    """Protocol for LLM providers. Implementations must satisfy it structurally."""
    
    async def agenerate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        purpose: str,
        temperature: float = 0.2,
    ) -> tuple[T, int, int, float]:
        """
        Generate structured output adhering to a Pydantic schema.
        Returns: (parsed_instance, tokens_in, tokens_out, cost_usd)
        """
        ...
