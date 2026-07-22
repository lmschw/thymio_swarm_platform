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
        self.tracking_verbose = False

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

    async def broadcast_tracking(self, message):
        robots = await self.list_robots()
        for robot in robots.values():
            await self.send(robot, message)

    async def collect_logs(
        self,
        session_id,
        hosts,
        output_dir,
        delete_remote=True,
    ):
        robots = await self.list_robots()

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        tasks = []

        if hosts == []:
            hosts = robots

        for hostname in hosts:

            robot = robots.get(hostname)

            if robot is None:
                print(
                    f"{hostname}: not found"
                )
                continue

            destination = output_dir

            tasks.append(
                self._collect_logs_from_robot(
                    robot,
                    session_id,
                    destination,
                    delete_remote,
                )
            )

        print("Collecting from:")
        print(hosts)
        await asyncio.gather(
            *tasks
        )

    async def _collect_logs_from_robot(
        self,
        robot,
        session_id,
        destination,
        delete=False,
    ):
        reader, writer = await asyncio.open_connection(
            robot["ip"],
            robot["port"],
        )
        try:
            request = {
                "type": "collect_logs",
                "session_id": session_id,
                "delete": delete,
            }
            writer.write(
                (json.dumps(request) + "\n").encode()
            )
            await writer.drain()
            filename = None
            buffer = bytearray()
            while True:
                line = await reader.readline()
                if not line:
                    raise RuntimeError(
                        "Connection closed while receiving log."
                    )
                message = json.loads(line.decode())
                msg_type = message["type"]
                if msg_type == "logs_begin":
                    filename = message["filename"]
                    if filename is None:
                        return
                    print(
                        f"Receiving {filename} "
                        f"({message['size']} bytes, "
                        f"{message['chunks']} chunks)"
                    )
                elif msg_type == "logs_chunk":
                    chunk = base64.b64decode(
                        message["data"]
                    )
                    buffer.extend(chunk)
                elif msg_type == "logs_end":
                    break
                elif msg_type == "error":
                    raise RuntimeError(
                        f"{robot['ip']} returned error: {message.get('error')}"
                    )

                else:
                    raise RuntimeError(
                        f"Unexpected message type {msg_type}: {message}"
                    )
            destination.mkdir(
                parents=True,
                exist_ok=True,
            )
            path = destination / filename
            with open(path, "wb") as f:
                f.write(buffer)
            print(
                f"Saved log to {path}"
            )
        finally:
            writer.close()
            await writer.wait_closed()

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
        self.tracking_verbose = config.get("verbose", False)
        self.tracker = OptitrackClient(
            host=config["host"],
            hostname_map=config["hostname_map"],
            verbose=self.tracking_verbose,
        )
        await self.tracker.start()
        self.tracking_task = asyncio.create_task(
            self.tracking_loop()
        )

    async def tracking_loop(self):

        if self.tracking_verbose:
            print("[TRACKING LOOP] started", flush=True)

        while True:
            try:
                poses = await self.tracker.get_all_poses()

                if self.tracking_verbose:
                    print(
                        f"[TRACKING LOOP] poses={poses}",
                        flush=True,
                    )

                if poses:
                    await self.broadcast_tracking({
                        "type": "tracking_update",
                        "poses": {
                            hostname: pose.to_dict()
                            for hostname, pose in poses.items()
                        }
                    })

            except Exception as e:
                print(
                    f"[TRACKING LOOP ERROR] {repr(e)}",
                    flush=True,
                )

            await asyncio.sleep(0.5)