import pytest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from core.audit import AuditTrail
from core.models import TripRequest
from core.planner.graph import create_planner_graph
from core.planner.limits import CircuitBreakers, LimitConfig
from core.telemetry import get_tracer_provider, record_token_usage, trace_genai_span


@pytest.fixture
def memory_exporter():
    exporter = InMemorySpanExporter()
    processor = SimpleSpanProcessor(exporter)
    provider = get_tracer_provider()
    provider.add_span_processor(processor)
    yield exporter
    exporter.clear()

def test_trace_genai_span_attributes(memory_exporter):
    with trace_genai_span("test_step", purpose="test_purpose", model="test_model", provider="test_provider", step_index=2) as span:
        record_token_usage(span, tokens_in=120, tokens_out=45)

    spans = memory_exporter.get_finished_spans()
    matching = [s for s in spans if s.name == "test_step"]
    assert len(matching) >= 1
    s = matching[-1]
    assert s.name == "test_step"
    assert s.attributes["gen_ai.system"] == "test_provider"
    assert s.attributes["gen_ai.request.model"] == "test_model"
    assert s.attributes["tripagent.purpose"] == "test_purpose"
    assert s.attributes["tripagent.step_index"] == 2
    assert s.attributes["gen_ai.usage.input_tokens"] == 120
    assert s.attributes["gen_ai.usage.output_tokens"] == 45
    assert "tripagent.latency_ms" in s.attributes
    assert s.attributes["tripagent.latency_ms"] >= 0

def test_graph_emits_telemetry_spans(memory_exporter):
    breakers = CircuitBreakers(LimitConfig())
    graph = create_planner_graph(breakers)

    initial_state = {
        "request": TripRequest(
            request_text="test otel trip",
            constraints=[],
            party_size=1,
            budget=500.0,
            days=2,
        ),
        "audit_trail": AuditTrail(),
        "step_count": 0,
        "total_tokens": 0,
        "total_cost": 0.0,
        "replan_count": 0,
    }

    graph.invoke(initial_state)

    spans = memory_exporter.get_finished_spans()
    span_names = [s.name for s in spans]
    # Check that core LangGraph nodes emitted spans
    assert "parse_constraints" in span_names
    assert "retrieve" in span_names
    assert "draft_itinerary" in span_names
    assert "validate" in span_names
    assert "finalise" in span_names

    # Check semantic conventions on one of the spans
    val_span = next(s for s in spans if s.name == "validate")
    assert val_span.attributes["tripagent.purpose"] == "deterministic_validation"
    assert val_span.attributes["gen_ai.system"] == "local"
