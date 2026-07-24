import uuid
import asyncio
from pathlib import Path

class SwarmSession:


    def __init__(self, client, project, name=None, hosts=[]):
        self.client = client
        self.project = project
        self.hosts = hosts

        self.session_id = (
            name
            or f"session-{uuid.uuid4().hex[:8]}"
        )

    async def start(self, experiment, config=None):
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
        await self.client.broadcast({
            "type": "pause",
            "session_id": self.session_id,
        })

    async def resume(self):
        await self.client.broadcast({
            "type": "resume",
            "session_id": self.session_id,
        })

    async def stop(self):
        if self.client.tracking_task:
            self.client.tracking_task.cancel()
        if self.client.tracker:
            self.client.tracker.stop()
        await self.client.broadcast({
            "type": "stop",
            "session_id": self.session_id,
        })

    async def collect_logs(self, output_dir="results", delete_remote=True):
        await self.client.collect_logs(
            session_id=self.session_id,
            hosts=self.hosts,
            output_dir=Path(output_dir) / self.session_id,
            delete_remote=delete_remote,
        )
    
    async def delete_logs(self):
        await self.client.delete_logs(
            self.session_id,
            self.hosts
        )