from pathlib import Path
import subprocess

from .loader import ProjectLoader


class ProjectManager:

    def __init__(self, projects_dir: Path):
        self.projects_dir = Path(projects_dir)
        self.projects_dir.mkdir(parents=True, exist_ok=True)

        self.loader = ProjectLoader()
        self.project = None

    def clone(self, repository: str):
        name = repository.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        destination = self.projects_dir / name
        if destination.exists():
            return destination
        subprocess.run(
            [
                "git",
                "clone",
                repository,
                str(destination),
            ],
            check=True,
        )
        return destination

    def update(self, project: str):
        path = self.projects_dir / project
        subprocess.run(
            ["git", "-C", str(path), "pull"],
            check=True,
        )

    def activate(self, project: str):
        path = self.projects_dir / project
        self.project = self.loader.load(path)
        return self.project

    def current(self):
        return self.project

    def experiment(self, name: str):
        if self.project is None:
            raise RuntimeError("No active project.")
        return self.project.experiment(name)