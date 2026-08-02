from pathlib import Path
import subprocess
import yaml

from swarm_platform.controller.session import SwarmSession


class Project:

    """
    Manages the project code, the client and the hosts of the project.
    """

    def __init__(self, client, repository: str, hosts: list, local_root: str | Path = "projects"):
        """
        Params:
            - client (SwarmClient): the client that manages the connection to the coordinator and the pis.
            - repository (string): the link to the github repository with the project code
            - hosts (list[string]): the list of hostnames of pis that are targetted. Pass an empty list for all available pis.
            - local_root (string or Path): where the code should be stored.
        """

        self.client = client
        self.repository = repository
        self.hosts = hosts

        self.local_path = Path(local_root) / self._repo_name()

        self.config = None


    def _repo_name(self):
        """
        Determines the name of the repository from the link.

        Returns the name of the repository (string).
        """
        name = self.repository.rstrip("/").split("/")[-1]

        if name.endswith(".git"):
            name = name[:-4]

        return name


    # --------------------------
    # Local controller project
    # --------------------------

    def clone_local(self):
        """
        Clone the project repository locally on the client machine.

        Returns nothing.
        """
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
        """
        Updates the local copy of the project github repository.

        Returns nothing.
        """
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
        """
        Loads the project config that was passed at instantiation.

        Returns nothing.
        """
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
        """
        Retrieves the config for a specific experiment.

        Params:
            - name (string): the name of the experiment.

        Returns the config. Raises a KeyError if the experiment does not exist in the config.
        """
        self.load_config()

        try:
            return self.config["experiments"][name]

        except KeyError:
            raise KeyError(
                f"Unknown experiment '{name}'"
            )


    @property
    def tracking(self):
        """
        Checks if tracking is enabled for the current experiment.

        Returns boolean whether position tracking is enabled.
        """
        self.load_config()

        return self.config.get(
            "tracking"
        )


    # --------------------------
    # Remote projects
    # --------------------------

    async def install(self):
        """
        Clones and installs the project repository on the pis.

        Returns nothing.
        """
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
        """
        Pulls from the remote github repository and thereby updates the project code on the pis.

        Returns nothing.
        """
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
        """
        Activates the project on all pis or on the specified subset of hosts.

        Returns nothing.
        """
        responses = await self.client.broadcast({
            "type": "activate_project",
            "hosts": self.hosts,
        })

        self.client._check_results(
            "Project activation",
            responses,
        )


    def session(self, name=None):
        """
        Creates a SwarmSession object for the current project.

        Params:
            - name (string): the name of the session.
        
        Returns the SwarmSession object.
        """
        return SwarmSession(
            self.client,
            project=self,
            name=name,
            hosts=self.hosts,
        )