from typing import Literal, Any
from pydantic import BaseModel, Field

class ScenarioConstraints(BaseModel):
    days: int | None = None
    budget_eur: float | None = None
    party_size: int | None = None
    excluded_modes: list[str] = Field(default_factory=list)
    # Allows flexibility for other constraints
    class Config:
        extra = "allow"

class Scenario(BaseModel):
    request_text: str
    constraints: ScenarioConstraints
    expected_feasibility: Literal["feasible", "infeasible"]
    expected_conflicts: list[str] = Field(default_factory=list)
    forbidden_behaviours: list[str]
    
    # Track the file it was loaded from for debugging
    _filename: str = ""
