import asyncio
import json
from pathlib import Path
import base64
import zipfile
import io

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

    async def collect_logs(self, session_id, output_dir, delete_remote=False):
        robots = await self.list_robots()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"[COLLECT LOGS] session_id={session_id} output_dir={output_dir} delete_remote={delete_remote}")

        for robot_id, robot in robots.items():

            response = await self.send(
                robot,
                {
                    "type": "collect_logs",
                    "session_id": session_id,
                    "delete": delete_remote,
                },
            )

            if response["content"] is None:
                print(f"[{robot_id}] No logs found for session {session_id}")
                continue

            data = base64.b64decode(response["content"])

            with zipfile.ZipFile(io.BytesIO(data)) as z:
                z.extractall(output_dir / robot_id)
    
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