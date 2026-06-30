import asyncio
import json


class SwarmClient:
    def __init__(self, coordinator_ip, coordinator_port=9100):
        self.coordinator_ip = coordinator_ip
        self.coordinator_port = coordinator_port

    async def list_robots(self):
        reader, writer = await asyncio.open_connection(
            self.coordinator_ip,
            self.coordinator_port
        )

        msg = {"type": "list"}
        writer.write((json.dumps(msg) + "\n").encode())
        await writer.drain()

        data = await reader.readline()
        writer.close()
        await writer.wait_closed()

        return json.loads(data.decode())["robots"]