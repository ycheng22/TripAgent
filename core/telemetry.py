from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Span

_provider = TracerProvider()
trace.set_tracer_provider(_provider)

tracer = trace.get_tracer("tripagent", "0.1.0")

def get_tracer_provider() -> TracerProvider:
    """Return the global TracerProvider instance for adding processors or exporters."""
    return _provider

@contextmanager
def trace_genai_span(
    name: str,
    purpose: str,
    model: str = "langgraph-deterministic",
    provider: str = "local",
    step_index: int | None = None,
) -> Generator[Span, None, None]:
    """
    OpenTelemetry context manager instrumented with GenAI semantic conventions.
    Records model, provider, latency, step index, and purpose tag.
    """
    start_time = time.perf_counter()
    with tracer.start_as_current_span(name) as span:
        span.set_attribute("gen_ai.system", provider)
        span.set_attribute("gen_ai.request.model", model)
        span.set_attribute("tripagent.purpose", purpose)
        if step_index is not None:
            span.set_attribute("tripagent.step_index", step_index)

        try:
            yield span
        finally:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            span.set_attribute("tripagent.latency_ms", latency_ms)

def record_token_usage(span: Span, tokens_in: int, tokens_out: int) -> None:
    """Record input and output tokens adhering to GenAI semantic conventions."""
    span.set_attribute("gen_ai.usage.input_tokens", tokens_in)
    span.set_attribute("gen_ai.usage.output_tokens", tokens_out)
