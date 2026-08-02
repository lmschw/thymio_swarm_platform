from dataclasses import dataclass
from pathlib import Path

from swarm_platform.projects.experiment_config import ExperimentConfig

@dataclass
class Project:
    """A loaded swarm project: its metadata and configured experiments.

    Attributes:
        name: Name of the project.
        version: Version string of the project.
        path: Filesystem path to the project directory.
        experiments: Mapping from experiment name to its configuration.
        tracking: Optional project-level tracking configuration.
    """

    name: str
    version: str
    path: Path

    experiments: dict[str, ExperimentConfig]

    tracking: dict | None = None


    def experiment(self, name: str) -> type:
        """Look up an experiment's class by name.

        Args:
            name: Name of the experiment to look up.

        Returns:
            The experiment's class.

        Raises:
            KeyError: If no experiment named ``name`` exists in this
                project.
        """

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


    def experiment_config(self, name: str) -> ExperimentConfig:
        """Look up an experiment's full configuration by name.

        Args:
            name: Name of the experiment to look up.

        Returns:
            The experiment's configuration.

        Raises:
            KeyError: If no experiment named ``name`` exists in this
                project.
        """

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