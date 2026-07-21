from dataclasses import dataclass
from pathlib import Path

from swarm_platform.projects.experiment_config import ExperimentConfig

@dataclass
class Project:

    name: str
    version: str
    path: Path

    experiments: dict[str, ExperimentConfig]

    tracking: dict | None = None


    def experiment(self, name: str):

        try:
            return self.experiments[name].cls

        except KeyError:
            available = ", ".join(
                sorted(self.experiments)
            )

            raise KeyError(
                f"Experiment '{name}' not found in project "
                f"'{self.name}'. "
                f"Available experiments: {available}"
            )


    def experiment_config(self, name: str):

        try:
            return self.experiments[name]

        except KeyError:
            available = ", ".join(
                sorted(self.experiments)
            )

            raise KeyError(
                f"Experiment '{name}' not found in project "
                f"'{self.name}'. "
                f"Available experiments: {available}"
            )