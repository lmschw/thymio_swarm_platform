import uuid
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from swarm_platform.controller.client import SwarmClient
    from swarm_platform.controller.project import Project

class SwarmSession:

    """
    Manages an experiment run.

    Wraps a single named experiment "session": starting, pausing,
    resuming and stopping an experiment on the target pis, as well as
    collecting and deleting the resulting logs.
    """

    def __init__(
        self,
        client: "SwarmClient",
        project: "Project",
        name: Optional[str] = None,
        hosts: List[str] = [],
    ) -> None:
        """
        Initializes the session with its client, project, name and target hosts.

        Params:
            - client (SwarmClient): the SwarmClient which manages the connection to the coordinator and the pis.
            - project (Project): the project that is currently being handled.
            - name (string) [optional]: the name of the session.
            - hosts (list[string]) [optional]: the hostnames of the target pis. If left empty, all available pis are targetted.
        """
        self.client = client
        self.project = project
        self.hosts = hosts

        self.session_id = (
            name
            or f"session-{uuid.uuid4().hex[:8]}"
        )

    async def start(
        self,
        experiment: str,
        config: Optional[Dict[str, Any]] = None,
        host_configs: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        """
        Starts a session and with it an experiment of the current project.

        Activates the project, looks up the experiment's config, starts
        tracking if the experiment requests it, and broadcasts the
        start request to the target hosts.

        Params:
            - experiment (string): the name of the experiment
            - config (dict) [optional]: the configuration of the experiment,
                shared by every targeted host.
            - host_configs (dict) [optional]: mapping of hostname to a
                config dict to merge on top of ``config`` for that host,
                so different robots can receive different experiment
                configuration (e.g. a different role/genome) in the same
                start.

        Raises:
            KeyError: If the experiment does not exist in the project config.
            RuntimeError: If any pi fails to start the experiment
                (raised by ``client._check_results``).
        """
        await self.project.activate()

        experiment_cfg = self.project.experiment_config(experiment)

        if experiment_cfg.get("tracking", False):
            await self.client.start_tracking(
                self.project.tracking
            )

        message = {
            "type": "start_experiment",
            "session_id": self.session_id,
            "name": experiment,
            "hosts": self.hosts,
            "config": config or {},
        }

        if host_configs:
            responses = await self.client.broadcast_per_host(
                message,
                host_configs,
            )
        else:
            responses = await self.client.broadcast(message)

        self.client._check_results(
            f"Starting experiment '{experiment}'",
            responses,
        )

    async def pause(self) -> None:
        """
        Pauses the current experiment.

        Broadcasts a pause request for this session to the target hosts.
        """
        await self.client.broadcast({
            "type": "pause",
            "session_id": self.session_id,
        })

    async def resume(self) -> None:
        """
        Resumes a paused experiment.

        Broadcasts a resume request for this session to the target hosts.
        """
        await self.client.broadcast({
            "type": "resume",
            "session_id": self.session_id,
        })

    async def stop(self) -> None:
        """
        Stops the current experiment as well as the tracking if applicable.

        Cancels the client's tracking task and stops its tracker, if
        any, then broadcasts a stop request for this session to the
        target hosts.
        """
        if self.client.tracking_task:
            self.client.tracking_task.cancel()
        if self.client.tracker:
            self.client.tracker.stop()
        await self.client.broadcast({
            "type": "stop",
            "session_id": self.session_id,
        })

    async def collect_logs(
        self,
        output_dir: str | Path = "results",
        delete_remote: bool = True,
    ) -> None:
        """
        Collect the logs from all hosts and saves them on the client computer.

        Params:
            - output_dir (string or Path) [optional]: the target directory on the client, where the logs should be saved.
            - delete_remote (boolean) [optional]: whether the logs should be deleted on the pis.
        """
        await self.client.collect_logs(
            session_id=self.session_id,
            hosts=self.hosts,
            output_dir=Path(output_dir) / self.session_id,
            delete_remote=delete_remote,
        )

    async def delete_logs(self) -> None:
        """
        Deletes the logs on the pis.

        Broadcasts a delete-logs request for this session to the target hosts.
        """
        await self.client.delete_logs(
            self.session_id,
            self.hosts
        )

    async def send_internal_update(self, update_type: str) -> None:
        """
        Sends a signal to the pis to cause an internal update event.
        """
        await self.client.broadcast({
            "type": "internal_update",
            "session_id": self.session_id,
            "hosts": self.hosts,
            "update_type": update_type
        })
