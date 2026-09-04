import os
import glob
import json
import datetime
from pydantic import ValidationError
from evals.models import Scenario
from app.settings import settings

class ScenarioSet:
    def __init__(self, directory: str = "evals/scenarios"):
        self.directory = directory
        self.scenarios: list[Scenario] = []
        self.created_at = datetime.datetime.now(datetime.timezone.utc)
        self.git_sha = settings.git_sha
        
        # In a real system, the scenario set version might be tracked separately.
        # Here we just use the git sha and count.
        self.version = f"v-{self.git_sha[:7] if self.git_sha != 'unknown' else 'unknown'}"
        
        self._load_scenarios()
        self.scenario_count = len(self.scenarios)

    def _load_scenarios(self):
        pattern = os.path.join(self.directory, "*.json")
        for path in glob.glob(pattern):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Fails loudly if malformed
                scenario = Scenario.model_validate(data)
                scenario._filename = os.path.basename(path)
                self.scenarios.append(scenario)
            except ValidationError as e:
                print(f"Error parsing scenario {path}: {e}")
                raise
            except Exception as e:
                print(f"Failed to read {path}: {e}")
                raise

    def __iter__(self):
        return iter(self.scenarios)
