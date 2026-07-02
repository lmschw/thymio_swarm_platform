import asyncio
import json

from swarm_platform.utils import config


class SwarmClient:
    def __init__(self, coordinator_ip, coordinator_port=9100):
        self.coordinator_ip = coordinator_ip
        self.coordinator_port = coordinator_port

    async def list_robots(self):
        response = await self._request({"type": "list"})
        return response["robots"]
    
    async def start_experiment(self, name, config=None):
        return await self._request({
            "type": "start_experiment",
            "name": name,
            "config": config or {}
        })
    
    async def stop_experiment(self):
        return await self._request({
            "type": "stop"
        })
    
    async def pause_experiment(self):
        return await self._request({
            "type": "pause"
        })
    
    async def update_all(self):
        return await self._request({
            "type": "update_code"
        })
    

    
    async def _request(self, msg: dict):
        reader, writer = await asyncio.open_connection(
            self.coordinator_ip,
            self.coordinator_port
        )

        writer.write((json.dumps(msg) + "\n").encode())
        await writer.drain()

        data = await reader.readline()

        writer.close()
        await writer.wait_closed()

        return json.loads(data.decode())