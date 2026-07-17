from dataclasses import dataclass
from pathlib import Path


@dataclass
class Project:
    name: str
    version: str
    path: Path

    experiments: dict[str, dict]
    tracking: dict | None = None

    def experiment(self, name: str):
        try:
            return self.experiments[name]["class"]
        except KeyError:
            available = ", ".join(sorted(self.experiments))
            raise KeyError(
                f"Experiment '{name}' not found in project '{self.name}'. "
                f"Available experiments: {available}"
            )

    def experiment_config(self, name: str):
        try:
            return self.experiments[name]
        except KeyError:
            available = ", ".join(sorted(self.experiments))
            raise KeyError(
                f"Experiment '{name}' not found in project '{self.name}'. "
                f"Available experiments: {available}"
            )

    def experiment_uses_tracking(self, name: str) -> bool:
        return self.experiments[name].get("tracking", False)