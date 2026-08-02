from pathlib import Path
import shutil
import subprocess

from typing import Optional

from .loader import ProjectLoader
from .project import Project, ExperimentConfig


class ProjectManager:
    """Manages the lifecycle of the active swarm project on disk.

    Handles cloning a project repository into the active project
    directory, keeping it up to date, loading it into memory, and
    looking up its experiments.
    """

    def __init__(self, active_dir: Path) -> None:
        """Initialize the manager for a given active project directory.

        Args:
            active_dir: Directory where the active project is (or will
                be) stored.
        """
        self.active_dir = Path(active_dir)
        self.loader = ProjectLoader()
        self.project: Optional[Project] = None

    def clone(self, repository: str) -> None:
        """Clone a project repository into the active project directory.

        Clones ``repository`` into a temporary directory, locates the
        single ``swarm_project.yaml`` manifest within it, and moves that
        manifest's parent directory into place as the active project
        directory, replacing any existing one.

        Args:
            repository: Git repository URL or path to clone.

        Raises:
            RuntimeError: If the cloned repository does not contain
                exactly one ``swarm_project.yaml`` file.
        """

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

    def update(self) -> None:
        """Discard local changes, sync the system clock, and pull latest.

        Restores the active project's working tree (discarding local
        changes), sets the system clock from an HTTP response's ``Date``
        header, then pulls the latest changes for the active project.
        """
        subprocess.run("git restore .", shell=True, check=True) # remove all local changes
        subprocess.run('sudo date -s "$(wget -qSO- --max-redirect=0 google.com 2>&1 | grep Date: | cut -d' ' -f5-8)Z"', shell=True, check=True)
        subprocess.run(
            ["git", "-C", str(self.active_dir), "pull"],
            check=True,
        )

    def activate(self) -> Project:
        """Load the active project from disk.

        Returns:
            The loaded project, which is also stored on ``self.project``.
        """
        self.project = self.loader.load(
            self.active_dir
        )

        return self.project

    def experiment(self, name: str) -> ExperimentConfig:
        """Look up a named experiment's configuration in the active project.

        Args:
            name: Name of the experiment to look up.

        Returns:
            The experiment's configuration.

        Raises:
            RuntimeError: If no project has been activated, or if no
                experiment named ``name`` exists in the active project.
        """
        if self.project is None:
            raise RuntimeError("No active project.")
        try:
            return self.project.experiments[name]
        except KeyError:
            raise RuntimeError(
                f"Experiment '{name}' not found."
            )