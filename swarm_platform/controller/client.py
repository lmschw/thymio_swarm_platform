import asyncio
import base64
import io
import json
import zipfile
from pathlib import Path

from swarm_platform.controller.project import Project
from swarm_platform.controller.session import SwarmSession


class SwarmClient:

    def __init__(self, coordinator_ip, coordinator_port=9100):
        self.coordinator_ip = coordinator_ip
        self.coordinator_port = coordinator_port

    def project(self, repository: str):
        return Project(self, repository)

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

        data = await reader.readline()

        writer.close()
        await writer.wait_closed()

        if not data:
            return {
                "type": "connection_closed"
            }

        return json.loads(data.decode())

    async def broadcast(self, message):
        robots = await self.list_robots()

        responses = await asyncio.gather(
            *(
                self.send(robot, message)
                for robot in robots.values()
            )
        )

        return {
            robot_id: response
            for (robot_id, _), response in zip(
                robots.items(),
                responses,
            )
        }

    async def collect_logs(self, session_id, output_dir, delete_remote=False):
        robots = await self.list_robots()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for robot_id, robot in robots.items():
            response = await self.send(
                robot,
                {
                    "type": "collect_logs",
                    "session_id": session_id,
                    "delete": delete_remote,
                },
            )

            if response.get("type") == "error":
                print(f"[{robot_id}] {response['error']}")
                continue

            content = response.get("content")

            if content is None:
                print(f"[{robot_id}] No logs.")
                continue

            data = base64.b64decode(content)
            destination = output_dir / robot_id
            destination.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                archive.extractall(destination)

    async def delete_logs(self, session_id):
        return await self.broadcast(
            {
                "type": "delete_logs",
                "session_id": session_id,
            }
        )