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
        print("Updating from", Path.cwd(), flush=True)

        subprocess.run(["pwd"])
        subprocess.run(["git", "remote", "-v"])
        subprocess.run(["git", "rev-parse", "--show-toplevel"])
        
        ROOT = Path(__file__).resolve().parents[2]

        subprocess.run(
            ["git", "-C", str(ROOT), "pull"],
            check=True,
        )

        subprocess.run(
            [str(Path.home()/".local/bin/uv"), "sync"],
            cwd=ROOT,
            check=True,
        )

    def activate(self, project: str):
        print(f"Activating project: {project}")
        print(f"Projects directory: {self.projects_dir}")
        path = self.projects_dir / project
        print(f"Loading project from: {path}")
        self.project = self.loader.load(path)
        print(f"Activated project: {self.project.name} (version {self.project.version})")
        return self.project

    def current(self):
        return self.project

    def experiment(self, name: str):
        if self.project is None:
            raise RuntimeError("No active project.")
        return self.project.experiment(name)