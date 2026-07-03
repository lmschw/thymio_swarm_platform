import asyncio
import json


class SwarmClient:

    def __init__(self, coordinator_ip, coordinator_port=9100):
        self.coordinator_ip = coordinator_ip
        self.coordinator_port = coordinator_port

    async def list_robots(self):

        reader, writer = await asyncio.open_connection(
            self.coordinator_ip,
            self.coordinator_port,
        )

        writer.write(b'{"type":"list"}\n')
        await writer.drain()

        response = json.loads((await reader.readline()).decode())

        writer.close()
        await writer.wait_closed()

        return response["robots"]

    async def send(self, robot, message):

        reader, writer = await asyncio.open_connection(
            robot["ip"],
            robot["port"],
        )

        writer.write((json.dumps(message) + "\n").encode())
        await writer.drain()

        response = json.loads((await reader.readline()).decode())

        writer.close()
        await writer.wait_closed()

        return response

    async def broadcast(self, message):

        robots = await self.list_robots()

        await asyncio.gather(
            *(
                self.send(robot, message)
                for robot in robots.values()
            )
        )

    async def activate_project(self, path: str):
        await self.broadcast({
            "type": "activate_project",
            "path": path
        })

    async def start_experiment(self, name: str, config: dict):
        await self.broadcast({
            "type": "start_experiment",
            "name": name,
            "config": config
        })