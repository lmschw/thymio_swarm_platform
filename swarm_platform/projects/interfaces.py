from typing import List, Protocol


class ProjectProvider(Protocol):
    """Interface for objects that provide access to experiment classes from a project."""

    def experiment(self, name: str) -> type:
        """Look up an experiment class by name.

        Args:
            name: The name of the experiment.

        Returns:
            The experiment class registered under that name.
        """
        pass

    def list_experiments(self) -> List[str]:
        """List the names of all available experiments.

        Returns:
            The names of the experiments provided by this project.
        """
        pass

    def reload(self) -> None:
        """Reload the project's experiments, picking up any code changes."""
        pass