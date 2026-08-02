from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import yaml

from swarm_platform.controller.session import SwarmSession

if TYPE_CHECKING:
    from swarm_platform.controller.client import SwarmClient


class Project:

    """
    Manages the project code, the client and the hosts of the project.

    Handles cloning/updating the project's git repository both locally
    (on the controller machine) and remotely (on the swarm's Raspberry
    Pis), loading the project's YAML configuration, and creating
    :class:`SwarmSession` objects to run experiments.
    """

    def __init__(
        self,
        client: "SwarmClient",
        repository: str,
        hosts: List[str],
        local_root: str | Path = "projects",
    ) -> None:
        """
        Initializes the project with its repository, client and target hosts.

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


    def _repo_name(self) -> str:
        """
        Determines the name of the repository from the link.

        Returns:
            The name of the repository, with any trailing slash and
            ``.git`` suffix stripped.
        """
        name = self.repository.rstrip("/").split("/")[-1]

        if name.endswith(".git"):
            name = name[:-4]

        return name


    # --------------------------
    # Local controller project
    # --------------------------

    def clone_local(self) -> None:
        """
        Clone the project repository locally on the client machine.

        Does nothing if the local path already exists.
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


    def update_local(self) -> None:
        """
        Updates the local copy of the project github repository.

        Clones the repository instead if it does not yet exist locally.
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


    def load_config(self) -> None:
        """
        Loads the project config that was passed at instantiation.

        Does nothing if the config was already loaded. The config is
        read from the ``swarm_project.yaml`` file at the root of the
        local repository copy.

        Raises:
            FileNotFoundError: If the ``swarm_project.yaml`` file is
                missing from the local repository copy.
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


    def experiment_config(self, name: str) -> Dict[str, Any]:
        """
        Retrieves the config for a specific experiment.

        Loads the project config first if it has not been loaded yet.

        Params:
            - name (string): the name of the experiment.

        Returns:
            The config dictionary for the named experiment.

        Raises:
            KeyError: If the experiment does not exist in the config.
        """
        self.load_config()

        try:
            return self.config["experiments"][name]

        except KeyError:
            raise KeyError(
                f"Unknown experiment '{name}'"
            )


    @property
    def tracking(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves the project-wide tracking configuration.

        Loads the project config first if it has not been loaded yet.

        Returns:
            The value stored under the ``tracking`` key of the project
            config (e.g. OptiTrack connection settings), or ``None`` if
            it is not set.
        """
        self.load_config()

        return self.config.get(
            "tracking"
        )


    # --------------------------
    # Remote projects
    # --------------------------

    async def install(self) -> None:
        """
        Clones and installs the project repository on the pis.

        Broadcasts a clone request to the target pis, clones the
        repository locally as well, and then activates the project.

        Raises:
            RuntimeError: If any pi fails to clone/install the project
                (raised by ``client._check_results``).
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


    async def update(self) -> None:
        """
        Pulls from the remote github repository and thereby updates the project code on the pis.

        Broadcasts an update request to the target pis, pulls the
        local repository copy as well, invalidates the cached config
        so it gets reloaded on next access, and then activates the
        project.

        Raises:
            RuntimeError: If any pi fails to update the project
                (raised by ``client._check_results``).
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


    async def activate(self) -> None:
        """
        Activates the project on all pis or on the specified subset of hosts.

        Raises:
            RuntimeError: If any pi fails to activate the project
                (raised by ``client._check_results``).
        """
        responses = await self.client.broadcast({
            "type": "activate_project",
            "hosts": self.hosts,
        })

        self.client._check_results(
            "Project activation",
            responses,
        )


    def session(self, name: Optional[str] = None) -> SwarmSession:
        """
        Creates a SwarmSession object for the current project.

        Params:
            - name (string) [optional]: the name of the session.

        Returns:
            The created SwarmSession object, targeting the same hosts
            as this project.
        """
        return SwarmSession(
            self.client,
            project=self,
            name=name,
            hosts=self.hosts,
        )