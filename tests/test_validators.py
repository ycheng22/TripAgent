import json
from pathlib import Path
from core.models import Itinerary, TripRequest, Constraint
from core.validators.budget import BudgetValidator
from core.validators.connectivity import ConnectivityValidator
from core.validators.opening_hours import OpeningHoursValidator
from core.validators.geography import GeographyValidator

def get_fixture(name: str) -> Itinerary:
    p = Path(f"tests/fixtures/must_fail/{name}.json")
    return Itinerary.model_validate_json(p.read_text())

def test_budget_breach():
    itin = get_fixture("budget_breach")
    req = TripRequest(request_text="t", constraints=[], party_size=1, budget=1000.0, days=1)
    violations = BudgetValidator().validate(itin, req)
    assert len(violations) > 0
    assert violations[0].breached_constraint == "budget"

def test_connectivity_teleport():
    itin = get_fixture("connectivity_teleport")
    req = TripRequest(request_text="t", constraints=[], party_size=1, budget=1000.0, days=1)
    violations = ConnectivityValidator().validate(itin, req)
    assert len(violations) > 0
    assert violations[0].breached_constraint == "connectivity"

def test_connectivity_visa():
    itin = get_fixture("connectivity_visa")
    req = TripRequest(request_text="t", constraints=[], party_size=1, budget=1000.0, days=1)
    violations = ConnectivityValidator().validate(itin, req)
    assert len(violations) > 0
    assert violations[0].breached_constraint == "connectivity"

def test_opening_hours_closed_day():
    itin = get_fixture("opening_hours_closed_day")
    req = TripRequest(request_text="t", constraints=[], party_size=1, budget=1000.0, days=1)
    violations = OpeningHoursValidator().validate(itin, req)
    assert len(violations) > 0
    assert violations[0].breached_constraint == "opening_hours"

def test_geography_overlap():
    itin = get_fixture("geography_overlap")
    req = TripRequest(request_text="t", constraints=[], party_size=1, budget=1000.0, days=1)
    violations = GeographyValidator().validate(itin, req)
    assert len(violations) > 0
    assert violations[0].breached_constraint == "geography"
