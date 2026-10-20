import datetime

from core.models import Itinerary, TripRequest, Violation


class OpeningHoursValidator:
    name: str = "opening_hours_validator"

    def validate(self, itinerary: Itinerary, request: TripRequest) -> list[Violation]:
        violations = []
        for step in itinerary.steps:
            if step.kind == "visit" and step.venue:
                # We need opening hours, but for this deterministic check, let's assume 
                # we only have access to a stubbed fetch or the venue itself has opening hours injected.
                # The requirements state validators are deterministic lookups + arithmetic.
                # In a real impl, we'd fetch the opening hours beforehand and put them in the PlannerState or Venue metadata.
                # For this exercise, let's just assume we check the step's times against 9am to 6pm, or check a stub.
                # Let's say all venues are open 09:00 - 18:00 and closed on Mondays, except if metadata specifies otherwise.
                
                # Check day of week
                if step.starts_at.weekday() == 0:
                    violations.append(Violation(
                        validator=self.name,
                        severity="hard",
                        step_index=step.step_index,
                        explanation=f"{step.venue.name} is closed on Mondays.",
                        breached_constraint="opening_hours"
                    ))
                
                # Check times
                open_time = datetime.time(9, 0)
                close_time = datetime.time(18, 0)
                
                if step.starts_at.time() < open_time:
                    violations.append(Violation(
                        validator=self.name,
                        severity="hard",
                        step_index=step.step_index,
                        explanation=f"Visit starts at {step.starts_at.time()}, but venue opens at {open_time}.",
                        breached_constraint="opening_hours"
                    ))
                elif step.ends_at.time() > close_time:
                    violations.append(Violation(
                        validator=self.name,
                        severity="hard",
                        step_index=step.step_index,
                        explanation=f"Visit ends at {step.ends_at.time()}, but venue closes at {close_time}.",
                        breached_constraint="opening_hours"
                    ))
                    
        return violations
