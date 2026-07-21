import importlib
import yaml

from pathlib import Path

from .project import Project, ExperimentConfig


class ProjectLoader:


    def load(self, path: Path) -> Project:
        yaml_path = path / "swarm_project.yaml"

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        experiments = {}

        for experiment_name, info in data.get(
            "experiments",
            {}
        ).items():
            module_name, class_name = (
                info["class"].rsplit(".", 1)
            )

            module = importlib.import_module(
                module_name
            )

            experiment_cls = getattr(
                module,
                class_name
            )

            experiments[experiment_name] = ExperimentConfig(
                cls=experiment_cls,
                tracking=info.get(
                    "tracking",
                    False
                ),
            )

        return Project(
            name=data["name"],
            version=data["version"],
            path=path,
            experiments=experiments,
            tracking=data.get(
                "tracking",
                None
            ),
        )