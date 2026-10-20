from core.models import Itinerary, TripRequest, Violation


class BudgetValidator:
    name: str = "budget_validator"

    def validate(self, itinerary: Itinerary, request: TripRequest) -> list[Violation]:
        violations = []
        step_costs = sum(step.cost for step in itinerary.steps if step.cost is not None)
        total_cost = max(itinerary.total_cost, step_costs)

        if total_cost > request.budget:
            violations.append(Violation(
                validator=self.name,
                severity="hard",
                step_index=None,
                explanation=f"Total cost {total_cost} exceeds budget of {request.budget}.",
                breached_constraint="budget"
            ))
        return violations
