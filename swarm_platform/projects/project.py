from dataclasses import dataclass
from pathlib import Path


@dataclass
class Project:
    name: str
    version: str
    path: Path
    experiments: dict[str, type]

    def experiment(self, name: str):
        try:
            return self.experiments[name]
        except KeyError:
            available = ", ".join(sorted(self.experiments))
            raise KeyError(
                f"Experiment '{name}' not found in project '{self.name}'. "
                f"Available experiments: {available}"
            )