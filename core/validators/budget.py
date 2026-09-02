from core.models import Itinerary, Violation, TripRequest
from core.validators.base import Validator

class BudgetValidator:
    name: str = "budget_validator"

    def validate(self, itinerary: Itinerary, request: TripRequest) -> list[Violation]:
        violations = []
        # Calculate total cost from all steps and itinerary cost, but let's just use itinerary cost + sum(step.cost)
        total_cost = itinerary.total_cost
        for step in itinerary.steps:
            if step.cost is not None:
                total_cost += step.cost

        if total_cost > request.budget:
            violations.append(Violation(
                validator=self.name,
                severity="hard",
                step_index=None,
                explanation=f"Total cost {total_cost} exceeds budget of {request.budget}.",
                breached_constraint="budget"
            ))
        return violations
