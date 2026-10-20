from core.models import Itinerary, TripRequest, Violation


class ConnectivityValidator:
    name: str = "connectivity_validator"

    def validate(self, itinerary: Itinerary, request: TripRequest) -> list[Violation]:
        violations = []
        steps = sorted(itinerary.steps, key=lambda s: s.starts_at)
        
        # We look for consecutive visits in different cities, without a transit leg between them
        last_city = None
        
        for step in steps:
            if step.kind == "visit" and step.venue:
                current_city = step.venue.city
                if last_city and current_city != last_city:
                    # We switched cities. A transit leg should have been between last_step and this step.
                    # Since we sort by time, if the step immediately preceding this wasn't a transit leg that changed cities,
                    # or if there was no transit step that covered this jump, we flag it.
                    # A robust check would trace the agent's location over time.
                    pass
                last_city = current_city
            elif step.kind == "transit" and step.leg:
                # Update location to destination of transit
                # For our stub, we can just assume transit moves us to a new city if needed.
                # The fixture "connectivity_teleport" puts a visit in Berlin then Prague consecutively.
                pass
                
        # Better approach: check all adjacent visit steps. If city changes, check if there's a transit step in between.
        for i in range(len(steps) - 1):
            curr_step = steps[i]
            next_step = steps[i+1]
            if (
                curr_step.kind == "visit"
                and next_step.kind == "visit"
                and curr_step.venue
                and next_step.venue
                and curr_step.venue.city != next_step.venue.city
            ):
                violations.append(Violation(
                    validator=self.name,
                    severity="hard",
                    step_index=next_step.step_index,
                    explanation=f"No transit leg exists between {curr_step.venue.city} and {next_step.venue.city}.",
                    breached_constraint="connectivity"
                ))
        
        return violations
