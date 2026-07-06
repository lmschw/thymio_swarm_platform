import uuid


class SwarmSession:

    def __init__(self, client, name=None):
        self.client = client
        self.session_id = name or f"session-{uuid.uuid4().hex[:8]}"

    async def activate_project(self, path: str):
        await self.client.activate_project(path)

    async def start(self, experiment, config=None):
        await self.client.broadcast({
            "type": "start_experiment",
            "session_id": self.session_id,
            "name": experiment,
            "config": config or {},
        })

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

    async def collect_logs(self):
        return await self.client.collect_logs(
            self.session_id
        )
    
    async def delete_logs(self):
        await self.client.delete_logs(
            self.session_id
        )