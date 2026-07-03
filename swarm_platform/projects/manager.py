from pathlib import Path

from .loader import ProjectLoader
from .exceptions import ExperimentNotFound


class ProjectManager:

    def __init__(self, project_directory: str | Path):
        self.project_directory = Path(project_directory)
        self.loader = ProjectLoader()
        self.project = self.loader.load(self.project_directory)

    def reload(self):
        self.project = self.loader.load(self.project_directory)

    def experiment(self, name: str):

        try:
            return self.project.experiments[name]

        except KeyError:
            raise ExperimentNotFound(name)

    def list_experiments(self):

        return sorted(self.project.experiments.keys())