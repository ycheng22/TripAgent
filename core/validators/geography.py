from core.models import Itinerary, Violation, TripRequest
import math

class GeographyValidator:
    name: str = "geography_validator"

    def validate(self, itinerary: Itinerary, request: TripRequest) -> list[Violation]:
        violations = []
        steps = sorted(itinerary.steps, key=lambda s: s.starts_at)
        
        for i in range(len(steps) - 1):
            curr_step = steps[i]
            next_step = steps[i+1]
            
            # Check overlap
            if next_step.starts_at < curr_step.ends_at:
                violations.append(Violation(
                    validator=self.name,
                    severity="hard",
                    step_index=next_step.step_index,
                    explanation="Overlapping time with previous step.",
                    breached_constraint="geography"
                ))
                continue
            
            # Check travel time for consecutive visits
            if curr_step.kind == "visit" and next_step.kind == "visit" and curr_step.venue and next_step.venue:
                if curr_step.venue.city == next_step.venue.city:
                    # Calculate haversine distance
                    lat1 = math.radians(curr_step.venue.coord.lat)
                    lon1 = math.radians(curr_step.venue.coord.lon)
                    lat2 = math.radians(next_step.venue.coord.lat)
                    lon2 = math.radians(next_step.venue.coord.lon)
                    dlon = lon2 - lon1
                    dlat = lat2 - lat1
                    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                    distance_km = 6371.0 * c
                    
                    walk_time_secs = (distance_km / 4.5) * 3600
                    time_gap_secs = (next_step.starts_at - curr_step.ends_at).total_seconds()
                    
                    if walk_time_secs > time_gap_secs:
                        violations.append(Violation(
                            validator=self.name,
                            severity="hard",
                            step_index=next_step.step_index,
                            explanation=f"Insufficient travel time. Requires {int(walk_time_secs/60)} mins to walk, but gap is {int(time_gap_secs/60)} mins.",
                            breached_constraint="geography"
                        ))
        return violations
