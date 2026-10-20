import datetime
from pathlib import Path

from core.models import Coordinate, Itinerary, ItineraryStep, TransitLeg, Venue

out_dir = Path("tests/fixtures/must_fail")
out_dir.mkdir(parents=True, exist_ok=True)

dt1 = datetime.datetime(2024, 6, 1, 10, 0)
dt2 = datetime.datetime(2024, 6, 1, 12, 0)

coord_a = Coordinate(lat=52.52, lon=13.40)
coord_b = Coordinate(lat=52.53, lon=13.41)

venue_a = Venue(venue_id="A", name="A", city="Berlin", coord=coord_a, source_id="s1", source_version="1")
venue_b = Venue(venue_id="B", name="B", city="Berlin", coord=coord_b, source_id="s1", source_version="1")

fixtures = {}

# 1. Budget violation
fixtures["budget_breach"] = Itinerary(
    itinerary_id="itin-1",
    total_cost=1500.0,
    currency="EUR",
    steps=[ItineraryStep(step_index=1, day=1, kind="visit", starts_at=dt1, ends_at=dt2, venue=venue_a, source_id="s1", source_version="1", cost=1500.0)]
)

# 2. Connectivity: teletransportation (no transit leg between cities)
venue_prague = Venue(venue_id="PRG", name="Prague Castle", city="Prague", coord=Coordinate(lat=50.07, lon=14.43), source_id="s", source_version="1")
fixtures["connectivity_teleport"] = Itinerary(
    itinerary_id="itin-2",
    total_cost=0.0,
    currency="EUR",
    steps=[
        ItineraryStep(step_index=1, day=1, kind="visit", starts_at=dt1, ends_at=dt2, venue=venue_a, source_id="s", source_version="1"),
        ItineraryStep(step_index=2, day=1, kind="visit", starts_at=dt2, ends_at=dt2 + datetime.timedelta(hours=2), venue=venue_prague, source_id="s", source_version="1")
    ]
)

# 3. Connectivity: Visa (Schengen -> London -> Schengen without UK Visa) - we just model it as missing transit leg
venue_london = Venue(venue_id="LON", name="London Eye", city="London", coord=Coordinate(lat=51.5, lon=-0.1), source_id="s", source_version="1")
fixtures["connectivity_visa"] = Itinerary(
    itinerary_id="itin-3",
    total_cost=0.0,
    currency="EUR",
    steps=[
        ItineraryStep(step_index=1, day=1, kind="visit", starts_at=dt1, ends_at=dt2, venue=venue_a, source_id="s", source_version="1"),
        # Suppose a leg exists, but London requires visa, we model as no leg exists. 
        # For the fixture, we just put transit, but we'll test that the leg doesn't exist in our DB later.
        # But wait, this is just an itinerary. If the itinerary has a transit leg, the validator will check it.
        # Let's say the itinerary has NO transit leg because none exists.
        ItineraryStep(step_index=2, day=1, kind="visit", starts_at=dt2, ends_at=dt2 + datetime.timedelta(hours=2), venue=venue_london, source_id="s", source_version="1")
    ]
)

# 4. Opening Hours: Closed on Mondays
fixtures["opening_hours_closed_day"] = Itinerary(
    itinerary_id="itin-4",
    total_cost=0.0,
    currency="EUR",
    steps=[ItineraryStep(step_index=1, day=1, kind="visit", starts_at=datetime.datetime(2024, 6, 3, 10, 0), ends_at=datetime.datetime(2024, 6, 3, 12, 0), venue=venue_a, source_id="s", source_version="1")] # June 3, 2024 is a Monday
)

# 5. Opening Hours: Visits before opening time
fixtures["opening_hours_before_open"] = Itinerary(
    itinerary_id="itin-5",
    total_cost=0.0,
    currency="EUR",
    steps=[ItineraryStep(step_index=1, day=1, kind="visit", starts_at=datetime.datetime(2024, 6, 4, 7, 0), ends_at=datetime.datetime(2024, 6, 4, 9, 0), venue=venue_a, source_id="s", source_version="1")] # Venue A opens at 9:00
)

# 6. Opening Hours: Visits after closing time
fixtures["opening_hours_after_close"] = Itinerary(
    itinerary_id="itin-6",
    total_cost=0.0,
    currency="EUR",
    steps=[ItineraryStep(step_index=1, day=1, kind="visit", starts_at=datetime.datetime(2024, 6, 4, 17, 0), ends_at=datetime.datetime(2024, 6, 4, 19, 0), venue=venue_a, source_id="s", source_version="1")] # Venue A closes at 18:00
)

# 7. Geography: Overlapping times / Teleporting in same city (travel time is impossible)
# 1 minute between A and B, which are distant
fixtures["geography_overlap"] = Itinerary(
    itinerary_id="itin-7",
    total_cost=0.0,
    currency="EUR",
    steps=[
        ItineraryStep(step_index=1, day=1, kind="visit", starts_at=datetime.datetime(2024, 6, 4, 10, 0), ends_at=datetime.datetime(2024, 6, 4, 12, 0), venue=venue_a, source_id="s", source_version="1"),
        ItineraryStep(step_index=2, day=1, kind="visit", starts_at=datetime.datetime(2024, 6, 4, 12, 1), ends_at=datetime.datetime(2024, 6, 4, 14, 0), venue=venue_b, source_id="s", source_version="1")
    ]
)

# 8. Geography: Missing transit leg for long intra-city distance
coord_c = Coordinate(lat=52.52, lon=13.60) # Far away
venue_c = Venue(venue_id="C", name="C", city="Berlin", coord=coord_c, source_id="s", source_version="1")
fixtures["geography_too_far_to_walk"] = Itinerary(
    itinerary_id="itin-8",
    total_cost=0.0,
    currency="EUR",
    steps=[
        ItineraryStep(step_index=1, day=1, kind="visit", starts_at=datetime.datetime(2024, 6, 4, 10, 0), ends_at=datetime.datetime(2024, 6, 4, 12, 0), venue=venue_a, source_id="s", source_version="1"),
        ItineraryStep(step_index=2, day=1, kind="visit", starts_at=datetime.datetime(2024, 6, 4, 13, 0), ends_at=datetime.datetime(2024, 6, 4, 15, 0), venue=venue_c, source_id="s", source_version="1")
    ]
)

# 9. Budget: Over budget with transit
fixtures["budget_transit_breach"] = Itinerary(
    itinerary_id="itin-9",
    total_cost=100.0,
    currency="EUR",
    steps=[
        ItineraryStep(step_index=1, day=1, kind="transit", starts_at=dt1, ends_at=dt2, leg=TransitLeg(trip_id="1", from_stop="A", to_stop="B", depart_at=dt1, arrive_at=dt2, feed_version="1", mode="train"), source_id="s", source_version="1", cost=1500.0)
    ]
)

# 10. Geography: Negative travel time
fixtures["geography_negative_time"] = Itinerary(
    itinerary_id="itin-10",
    total_cost=0.0,
    currency="EUR",
    steps=[
        ItineraryStep(step_index=1, day=1, kind="visit", starts_at=datetime.datetime(2024, 6, 4, 10, 0), ends_at=datetime.datetime(2024, 6, 4, 12, 0), venue=venue_a, source_id="s", source_version="1"),
        ItineraryStep(step_index=2, day=1, kind="visit", starts_at=datetime.datetime(2024, 6, 4, 11, 0), ends_at=datetime.datetime(2024, 6, 4, 13, 0), venue=venue_b, source_id="s", source_version="1")
    ]
)

for name, itin in fixtures.items():
    p = out_dir / f"{name}.json"
    p.write_text(itin.model_dump_json(indent=2))

print("Created 10 fixtures")
