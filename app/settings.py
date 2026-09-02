import os
from pydantic import BaseModel

class Settings(BaseModel):
    allowed_origins: list[str]
    max_steps: int
    max_tokens_per_task: int
    max_cost_per_task: float
    max_replans: int

def load_settings() -> Settings:
    origins_raw = os.environ.get("ALLOWED_ORIGINS", "")
    origins = [x.strip() for x in origins_raw.split(",") if x.strip()]
    
    return Settings(
        allowed_origins=origins,
        max_steps=int(os.environ.get("MAX_STEPS", "25")),
        max_tokens_per_task=int(os.environ.get("MAX_TOKENS_PER_TASK", "60000")),
        max_cost_per_task=float(os.environ.get("MAX_COST_PER_TASK", "0.05")),
        max_replans=int(os.environ.get("MAX_REPLANS", "3"))
    )

settings = load_settings()
