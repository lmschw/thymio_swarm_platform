from pathlib import Path
import importlib
import yaml
import sys

from .exceptions import ProjectLoadError
from .project import Project


class ProjectLoader:

    MANIFEST = "swarm_project.yaml"

    def load(self, directory: str | Path) -> Project:

        directory = Path(directory)

        manifest = directory / self.MANIFEST

        if not manifest.exists():
            raise ProjectLoadError(
                f"No {self.MANIFEST} found in {directory}"
            )

        with manifest.open() as f:
            data = yaml.safe_load(f)

        print(data)

        if str(directory) not in sys.path:
            sys.path.insert(0, str(directory))

        experiments = {}

        for experiment_name, info in data["experiments"].items():
            module_name, class_name = info["class"].rsplit(".", 1)

            module = importlib.import_module(module_name)
            experiment_cls = getattr(module, class_name)

            experiments[experiment_name] = {
                "class": experiment_cls,
                "tracking": info.get("tracking", False),
            }

        return Project(
            name=data["name"],
            version=data["version"],
            path=directory,
            experiments=experiments,
            tracking=data.get("tracking"),
        )