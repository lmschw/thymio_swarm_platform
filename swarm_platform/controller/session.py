import uuid
import asyncio
from pathlib import Path

class SwarmSession:

    """
    Manages an experiment run.
    """

    def __init__(self, client, project, name=None, hosts=[]):
        """
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

    async def start(self, experiment, config=None):
        """
        Starts a session and with it an experiment of the current project.

        Params:
            - experiment (string): the name of the experiment
            - config (dict) [optional]: the configuration of the experiment.

        Returns nothing.
        """
        await self.project.activate()

        experiment_cfg = self.project.experiment_config(experiment)

        if experiment_cfg.get("tracking", False):
            await self.client.start_tracking(
                self.project.tracking
            )


        responses = await self.client.broadcast({
            "type": "start_experiment",
            "session_id": self.session_id,
            "name": experiment,
            "hosts": self.hosts,
            "config": config or {},
        })

        self.client._check_results(
            f"Starting experiment '{experiment}'",
            responses,
        )

    async def pause(self):
        """
        Pauses the current experiment.

        Returns nothing.
        """
        await self.client.broadcast({
            "type": "pause",
            "session_id": self.session_id,
        })

    async def resume(self):
        """
        Resumes a paused experiment.

        Returns nothing.
        """
        await self.client.broadcast({
            "type": "resume",
            "session_id": self.session_id,
        })

    async def stop(self):
        """
        Stops the current experiment as well as the tracking if applicable.

        Returns nothing.
        """
        if self.client.tracking_task:
            self.client.tracking_task.cancel()
        if self.client.tracker:
            self.client.tracker.stop()
        await self.client.broadcast({
            "type": "stop",
            "session_id": self.session_id,
        })

    async def collect_logs(self, output_dir="results", delete_remote=True):
        """
        Collect the logs from all hosts and saves them on the client computer.

        Params:
            - output_dir (string) [optional]: the target directory on the client, where the logs should be saved.
            - delete_remote (boolean) [optional]: whether the logs should be deleted on the pis.

        Returns nothing.
        """
        await self.client.collect_logs(
            session_id=self.session_id,
            hosts=self.hosts,
            output_dir=Path(output_dir) / self.session_id,
            delete_remote=delete_remote,
        )
    
    async def delete_logs(self):
        """
        Deletes the logs on the pis.

        Returns nothing.
        """
        await self.client.delete_logs(
            self.session_id,
            self.hosts
        )