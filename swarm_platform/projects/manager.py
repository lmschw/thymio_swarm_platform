from pathlib import Path

from .loader import ProjectLoader
from .exceptions import ExperimentNotFound


class ProjectManager:
    def __init__(self, path: str):
        self.project = None
        self.activate(path)

    def activate(self, path: str):
        self.project = ProjectLoader().load(path)

    def experiment(self, name: str):
        return self.project.experiments[name]

    def list_experiments(self):
        return list(self.project.experiments.keys())

    def reload(self):
        if self.project:
            self.activate(self.project.path)