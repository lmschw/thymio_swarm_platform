import uuid
from pathlib import Path

class SwarmSession:


    def __init__(self, client, project, name=None):
        self.client = client
        self.project = project

        self.session_id = (
            name
            or f"session-{uuid.uuid4().hex[:8]}"
        )

    async def start(self, experiment, config=None):
        response = await self.project.activate()

        failed = [
            robot
            for robot, result in response.items()
            if result.get("type") == "error"
        ]

        if failed:
            raise RuntimeError(
                "Failed to activate project "
                f"'{self.project.name}' on: {', '.join(failed)}"
            )

        response = await self.client.broadcast({
            "type": "start_experiment",
            "session_id": self.session_id,
            "name": experiment,
            "config": config or {},
        })

        failed = [
            robot
            for robot, result in response.items()
            if result.get("type") == "error"
        ]

        if failed:
            raise RuntimeError(
                "Failed to start experiment "
                f"'{experiment}' on: {', '.join(failed)}"
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
        await self.client.broadcast({
            "type": "stop",
            "session_id": self.session_id,
        })

    async def collect_logs(self, output_dir="results", delete_remote=True):
        await self.client.collect_logs(
            session_id=self.session_id,
            output_dir=Path(output_dir) / self.session_id,
            delete_remote=delete_remote,
        )
    
    async def delete_logs(self):
        await self.client.delete_logs(
            self.session_id
        )