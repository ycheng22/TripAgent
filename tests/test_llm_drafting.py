import datetime
from typing import TypeVar

import pytest
from pydantic import BaseModel

from core.audit import AuditTrail
from core.models import Coordinate, Itinerary, ItineraryStep, TripRequest, Venue
from core.planner.graph import create_planner_graph
from core.planner.limits import CircuitBreakers, LimitConfig
from providers.base import LLMProvider

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    def __init__(self, responses: list[Itinerary] | None = None) -> None:
        self.provider_name = "mock_provider"
        self.model = "mock-model"
        self.calls: list[dict[str, str]] = []
        self._responses = list(responses) if responses else []
        self._index = 0

    async def agenerate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        purpose: str,
        temperature: float = 0.2,
    ) -> tuple[T, int, int, float]:
        self.calls.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "purpose": purpose,
        })
        if self._index < len(self._responses):
            resp = self._responses[self._index]
            self._index += 1
            return resp, 100, 50, 0.0001  # type: ignore[return-value]

        # Default minimal valid itinerary
        itin = Itinerary(
            itinerary_id="mock-itin",
            steps=[
                ItineraryStep(
                    step_index=1,
                    day=1,
                    kind="visit",
                    starts_at=datetime.datetime(2024, 6, 4, 10, 0, 0, tzinfo=datetime.UTC),
                    ends_at=datetime.datetime(2024, 6, 4, 12, 0, 0, tzinfo=datetime.UTC),
                    venue=Venue(
                        venue_id="par-eiffel",
                        name="Eiffel Tower",
                        city="Paris",
                        coord=Coordinate(lat=48.8584, lon=2.2945),
                        source_id="wikivoyage_paris",
                        source_version="2024-06-curated",
                    ),
                    cost=29.40,
                    source_id="wikivoyage_paris",
                    source_version="2024-06-curated",
                )
            ],
            total_cost=0.0,
            currency="EUR",
        )
        return itin, 100, 50, 0.0001  # type: ignore[return-value]


def test_mock_llm_drafting_tracks_tokens_and_audit() -> None:
    mock_provider = MockLLMProvider()
    breakers = CircuitBreakers(LimitConfig())
    graph = create_planner_graph(breakers, provider=mock_provider)

    req = TripRequest(
        request_text="I want to visit Paris for 1 day.",
        constraints=[],
        party_size=1,
        budget=100.0,
        days=1,
    )

    state = {
        "request": req,
        "constraints": [],
        "retrieved_hits": [],
        "itinerary": None,
        "violations": [],
        "audit_trail": AuditTrail(),
        "step_count": 0,
        "total_tokens": 0,
        "total_cost": 0.0,
        "replan_count": 0,
    }

    res = graph.invoke(state)

    assert res["status"] == "finalised"
    assert res["plan_result"].status == "finalised"
    assert len(mock_provider.calls) == 1
    assert "Eiffel Tower" in res["plan_result"].itinerary.steps[0].venue.name

    # Check token and cost tracking
    assert res["total_tokens"] == 150
    assert res["total_cost"] == pytest.approx(0.0001)

    # Check audit trail recorded the LLM drafting step
    draft_records = [r for r in res["audit_trail"].records if r.action_type == "draft_itinerary"]
    assert len(draft_records) == 1
    assert draft_records[0].source_id == "mock_provider"
    assert draft_records[0].source_version == "mock-model"
    assert draft_records[0].tokens_in == 100
    assert draft_records[0].tokens_out == 50


def test_mock_llm_replan_critique_flow() -> None:
    # Response 1: Exceeds budget (150.0 > 100.0) -> triggers violation & replan
    bad_itin = Itinerary(
        itinerary_id="bad-itin",
        steps=[
            ItineraryStep(
                step_index=1,
                day=1,
                kind="visit",
                starts_at=datetime.datetime(2024, 6, 4, 10, 0, 0, tzinfo=datetime.UTC),
                ends_at=datetime.datetime(2024, 6, 4, 12, 0, 0, tzinfo=datetime.UTC),
                venue=Venue(
                    venue_id="par-eiffel",
                    name="Eiffel Tower",
                    city="Paris",
                    coord=Coordinate(lat=48.8584, lon=2.2945),
                    source_id="wikivoyage_paris",
                    source_version="2024-06-curated",
                ),
                cost=150.0,
                source_id="wikivoyage_paris",
                source_version="2024-06-curated",
            )
        ],
        total_cost=0.0,
        currency="EUR",
    )

    # Response 2: Fixed cost within budget (29.40 <= 100.0)
    good_itin = Itinerary(
        itinerary_id="good-itin",
        steps=[
            ItineraryStep(
                step_index=1,
                day=1,
                kind="visit",
                starts_at=datetime.datetime(2024, 6, 4, 10, 0, 0, tzinfo=datetime.UTC),
                ends_at=datetime.datetime(2024, 6, 4, 12, 0, 0, tzinfo=datetime.UTC),
                venue=Venue(
                    venue_id="par-eiffel",
                    name="Eiffel Tower",
                    city="Paris",
                    coord=Coordinate(lat=48.8584, lon=2.2945),
                    source_id="wikivoyage_paris",
                    source_version="2024-06-curated",
                ),
                cost=29.40,
                source_id="wikivoyage_paris",
                source_version="2024-06-curated",
            )
        ],
        total_cost=0.0,
        currency="EUR",
    )

    mock_provider = MockLLMProvider(responses=[bad_itin, good_itin])
    breakers = CircuitBreakers(LimitConfig(max_replans=2))
    graph = create_planner_graph(breakers, provider=mock_provider)

    req = TripRequest(
        request_text="Trip to Paris",
        constraints=[],
        party_size=1,
        budget=100.0,
        days=1,
    )

    state = {
        "request": req,
        "constraints": [],
        "retrieved_hits": [],
        "itinerary": None,
        "violations": [],
        "audit_trail": AuditTrail(),
        "step_count": 0,
        "total_tokens": 0,
        "total_cost": 0.0,
        "replan_count": 0,
    }

    res = graph.invoke(state)

    assert res["status"] == "finalised"
    assert res["plan_result"].status == "finalised"
    assert len(mock_provider.calls) == 2

    # Verify that the second call received the critique about the budget violation
    second_system_prompt = mock_provider.calls[1]["system_prompt"]
    assert "PREVIOUS ATTEMPT FAILED DETERMINISTIC VALIDATION" in second_system_prompt
    assert "budget" in second_system_prompt.lower()
    assert res["replan_count"] == 1
