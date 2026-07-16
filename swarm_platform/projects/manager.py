from pathlib import Path
import shutil
import subprocess

from .loader import ProjectLoader


class ProjectManager:

    def __init__(self, active_dir: Path):
        self.active_dir = Path(active_dir)
        self.loader = ProjectLoader()
        self.project = None

    def clone(self, repository: str):

        tmp = self.active_dir.parent / "_clone_tmp"

        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(self.active_dir, ignore_errors=True)

        subprocess.run(
            ["git", "clone", repository, str(tmp)],
            check=True,
        )

        manifest = list(tmp.rglob("swarm_project.yaml"))

        if len(manifest) != 1:
            raise RuntimeError(
                f"Expected exactly one swarm_project.yaml, found {len(manifest)}."
            )

        project_root = manifest[0].parent

        shutil.move(str(project_root), str(self.active_dir))

        shutil.rmtree(tmp, ignore_errors=True)

    def update(self):
        subprocess.run("git restore .", shell=True, check=True) # remove all local changes
        subprocess.run('sudo date -s "$(wget -qSO- --max-redirect=0 google.com 2>&1 | grep Date: | cut -d' ' -f5-8)Z"', shell=True, check=True)
        subprocess.run(
            ["git", "-C", str(self.active_dir), "pull"],
            check=True,
        )

    def activate(self):
        self.project = self.loader.load(
            self.active_dir
        )

        return self.project
    
    def experiment(self, name: str):
        if self.project is None:
            raise RuntimeError("No active project.")
        try:
            return self.project.experiments[name]
        except KeyError:
            raise RuntimeError(
                f"Experiment '{name}' not found."
            )