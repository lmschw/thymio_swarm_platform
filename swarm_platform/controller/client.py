import asyncio
import base64
import io
import json
import zipfile
from pathlib import Path

from swarm_platform.controller.project import Project


class SwarmClient:

    def __init__(self, coordinator_ip, coordinator_port=9100):
        self.coordinator_ip = coordinator_ip
        self.coordinator_port = coordinator_port
        self.tracker = None
        self.tracking_task = None

    def project(self, repository: str, hosts: list = []):
        return Project(self, repository, hosts)

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
        last_error = None

        for _ in range(10):
            try:
                reader, writer = await asyncio.open_connection(
                    robot["ip"],
                    robot["port"],
                )
                break

            except OSError as e:
                last_error = e
                await asyncio.sleep(0.5)

        else:
            return {
                "type": "error",
                "error": str(last_error),
            }

        try:
            writer.write((json.dumps(message) + "\n").encode())
            await writer.drain()

            data = await reader.readline()

            if not data:
                return {"type": "connection_closed"}

            return json.loads(data.decode())

        finally:
            writer.close()
            await writer.wait_closed()

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

    async def collect_logs(self, session_id, hosts, output_dir, delete_remote=False):
        robots = await self.list_robots()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for robot_id, robot in robots.items():
            response = await self.send(
                robot,
                {
                    "type": "collect_logs",
                    "session_id": session_id,
                    "hosts": hosts,
                    "delete": delete_remote,
                },
            )

            if response.get("type") == "error":
                print(f"[{robot_id}] {response['error']}")
                continue

            content = response.get("content")

            if content is None:
                if hosts == [] or robot_id in hosts:
                    print(f"[{robot_id}] No logs.")
                continue

            data = base64.b64decode(content)
            destination = output_dir / robot_id
            destination.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                archive.extractall(destination)

    async def delete_logs(self, session_id, hosts):
        return await self.broadcast(
            {
                "type": "delete_logs",
                "session_id": session_id,
                "hosts": hosts,
            }
        )
    
    async def identify(self, hostname: str):
        responses = await self.broadcast({
            "type": "identify",
            "hostname": hostname,
        })
        self._check_results(
            f"Identify '{hostname}'",
            responses,
        )

    def _check_results(self, action, responses):
        failures = []
        for robot_id, response in responses.items():
            if response.get("type") == "error":
                failures.append(
                    f"{robot_id}: {response.get('error')}"
                )
        if failures:
            raise RuntimeError(
                f"{action} failed:\n  " + "\n  ".join(failures)
            )
        
    async def start_tracking(self, config):
        from swarm_platform.tracking.optitrack_client import (
            OptitrackClient
        )
        if self.tracker is not None:
            return
        self.tracker = OptitrackClient(
            host=config["host"],
            hostname_map=config["hostname_map"],
        )
        await self.tracker.start()
        self.tracking_task = asyncio.create_task(
            self.tracking_loop()
        )

    async def tracking_loop(self):
        print("[TRACKING LOOP] started", flush=True)

        while True:
            try:
                print("[TRACKING LOOP] tick", flush=True)

                poses = await self.tracker.get_all_poses()

                print(
                    f"[TRACKING LOOP] poses={poses}",
                    flush=True,
                )

                if poses:
                    await self.broadcast({
                        "type": "tracking_update",
                        "poses": {
                            hostname: pose.to_dict()
                            for hostname, pose in poses.items()
                        }
                    })

                await asyncio.sleep(0.1)

            except Exception as e:
                print(
                    f"[TRACKING LOOP ERROR] {repr(e)}",
                    flush=True,
                )