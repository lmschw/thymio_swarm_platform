import asyncio
import json
from pathlib import Path

from swarm_platform.controller.session import SwarmSession


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

    def session(self, name=None):
        return SwarmSession(self, name=name)

    async def collect_logs(self, session_id):

        robots = await self.list_robots()

        directory = Path("results") / session_id
        directory.mkdir(parents=True, exist_ok=True)

        for robot in robots.values():

            reply = await self.send(
                robot,
                {
                    "type": "get_log",
                    "session_id": session_id,
                },
            )

            if reply.get("type") != "log":
                continue

            path = directory / f"{reply['robot_id']}.csv"

            path.write_text(reply["content"])

        return directory
    
    async def delete_logs(self, session_id):
        robots = await self.list_robots()
        await asyncio.gather(
            *(
                self.send(
                    robot,
                    {
                        "type": "delete_log",
                        "session_id": session_id,
                    },
                )
                for robot in robots.values()
            )
        )