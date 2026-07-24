from pathlib import Path
import subprocess
import yaml

from swarm_platform.controller.session import SwarmSession


class Project:

    def __init__(
        self,
        client,
        repository: str,
        hosts: list,
        local_root: str | Path = "projects",
    ):
        self.client = client
        self.repository = repository
        self.hosts = hosts

        self.local_path = Path(local_root) / self._repo_name()

        self.config = None


    def _repo_name(self):

        name = self.repository.rstrip("/").split("/")[-1]

        if name.endswith(".git"):
            name = name[:-4]

        return name


    # --------------------------
    # Local controller project
    # --------------------------

    def clone_local(self):

        if self.local_path.exists():
            return

        self.local_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        subprocess.run(
            [
                "git",
                "clone",
                self.repository,
                str(self.local_path),
            ],
            check=True,
        )


    def update_local(self):

        if not self.local_path.exists():
            self.clone_local()
            return

        subprocess.run(
            [
                "git",
                "-C",
                str(self.local_path),
                "pull",
            ],
            check=True,
        )


    def load_config(self):

        if self.config is not None:
            return

        project_file = (
            self.local_path /
            "swarm_project.yaml"
        )

        if not project_file.exists():
            raise FileNotFoundError(
                f"Missing {project_file}"
            )

        with open(project_file) as f:
            self.config = yaml.safe_load(f)


    def experiment_config(self, name):

        self.load_config()

        try:
            return self.config["experiments"][name]

        except KeyError:
            raise KeyError(
                f"Unknown experiment '{name}'"
            )


    @property
    def tracking(self):

        self.load_config()

        return self.config.get(
            "tracking"
        )


    # --------------------------
    # Remote projects
    # --------------------------

    async def install(self):

        responses = await self.client.broadcast({
            "type": "clone_project",
            "repository": self.repository,
            "hosts": self.hosts,
        })

        self.client._check_results(
            "Project installation",
            responses,
        )

        self.clone_local()

        await self.activate()


    async def update(self):

        responses = await self.client.broadcast({
            "type": "update_project",
            "hosts": self.hosts,
        })

        self.client._check_results(
            "Project update",
            responses,
        )

        self.update_local()

        self.config = None

        await self.activate()


    async def activate(self):

        responses = await self.client.broadcast({
            "type": "activate_project",
            "hosts": self.hosts,
        })

        self.client._check_results(
            "Project activation",
            responses,
        )


    def session(self, name=None):

        return SwarmSession(
            self.client,
            project=self,
            name=name,
            hosts=self.hosts,
        )