import asyncio
import base64
import io
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from swarm_platform.controller.project import Project

class SwarmClient:

    """
    Handles the connection to the coordinator, the optitrack system and the swarm daemon 
    on the Raspberry Pi. Sends and retrieves messages as needed.
    """

    def __init__(self, coordinator_ip: str, coordinator_port: int = 9100) -> None:
        """Initialize the client with the coordinator's address.

        Args:
            coordinator_ip: The IP address of the coordinator instance that
                registers the pis.
            coordinator_port: The port of the coordinator instance that
                handles the communication.
        """
        self.coordinator_ip = coordinator_ip
        self.coordinator_port = coordinator_port

        # tracking is set up to be inactive by default and is activated if the experiment description requests it.
        self.tracker = None
        self.tracking_task = None
        self.tracking_verbose = False

    def project(self, repository: str, hosts: List[str] = []) -> Project:
        """Create the active project based on the project repository link and the hosts.

        Args:
            repository: The link to the project repository to be cloned and
                run on all hosts.
            hosts: The hostnames of the pis that should create this project.
                Defaults to an empty list which corresponds to all available
                hosts.

        Returns:
            A new Project instance wired up to this client.
        """
        return Project(self, repository, hosts)

    async def list_robots(self) -> Dict[str, Any]:
        """Retrieve all robots currently registered with the coordinator.

        Returns:
            A dict mapping robot hostnames to their info (e.g. ip/port).
        """
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

    async def send(self, robot: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to a single robot, retrying the connection if needed.

        Attempts to open the connection 10 times before failing, waiting
        0.5s between attempts.

        Args:
            robot: A dict containing the ip and port of the robot.
            message: A dict containing the details of the message,
                including message type.

        Returns:
            A dict with the response from the robot, or
            {"type": "connection_closed"} if the connection closed before a
            response arrived, or {"type": "error", "error": ...} if the
            connection could not be established after all retries.
        """
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

    async def broadcast(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast a message to all available robots concurrently.

        Args:
            message: A dict containing the details of the message,
                including message type.

        Returns:
            A dict containing the response for every robot, keyed by its
            hostname.
        """
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

    async def broadcast_per_host(
        self,
        base_message: Dict[str, Any],
        host_overrides: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Broadcast a message to all available robots, with a per-host config override.

        Like `broadcast`, but each robot's "config" is the base message's
        "config" merged with that robot's entry in `host_overrides` (if
        any), so different robots can receive different experiment
        configuration (e.g. a different role/genome) in the same
        `start_experiment` round.

        Args:
            base_message: The message to send, shared by all robots except
                for the per-host "config" override.
            host_overrides: Mapping of hostname to a config dict to merge
                on top of `base_message["config"]` for that host.

        Returns:
            A dict containing the response for every robot, keyed by its
            hostname.
        """
        robots = await self.list_robots()

        base_config = base_message.get("config", {})

        def _message_for(hostname: str) -> Dict[str, Any]:
            override = host_overrides.get(hostname)
            if not override:
                return base_message
            return {
                **base_message,
                "config": {**base_config, **override},
            }

        responses = await asyncio.gather(
            *(
                self.send(robot, _message_for(hostname))
                for hostname, robot in robots.items()
            )
        )

        return {
            robot_id: response
            for (robot_id, _), response in zip(
                robots.items(),
                responses,
            )
        }

    async def broadcast_tracking(self, message: Dict[str, Any]) -> None:
        """Broadcast a tracking update message to all available robots sequentially.

        Args:
            message: The dict containing the tracking information.
        """
        robots = await self.list_robots()
        for robot in robots.values():
            await self.send(robot, message)

    async def collect_logs(
        self,
        session_id: str,
        hosts: List[str],
        output_dir: Path,
        delete_remote: bool = True,
    ) -> None:
        """Collect the logs from all the robots and save them as .zip files.

        Args:
            session_id: The id of the current experiment session, can be set
                to anything at experiment creation.
            hosts: A list of the hostnames of the target pis, should be left
                empty to target all robots.
            output_dir: The path to the location where the logs should be
                stored; created if it doesn't already exist.
            delete_remote: Whether the logs on the pis should be deleted or
                kept after collecting them.
        """
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
        robot: Dict[str, Any],
        session_id: str,
        destination: Path,
        delete: bool = False,
    ) -> None:
        """Collect the logs of an experiment session from a single robot and save them to disk.

        Sends a "collect_logs" request to the robot, then reads the
        newline-delimited JSON reply stream: a "logs_begin" message
        announcing the filename/size/chunk count (returns immediately if
        there is no file), followed by "logs_chunk" messages whose
        base64-encoded data is decoded and appended to an in-memory buffer,
        until a "logs_end" message is received. The assembled bytes are
        then written to disk under ``destination``.

        Args:
            robot: The robot from which the logs should be collected, with
                its hostname, IP and port.
            session_id: The id of the current experiment session, can be set
                to anything at experiment creation.
            destination: The path to the location where the logs should be
                stored; created if it doesn't already exist.
            delete: Whether the logs on the pi should be deleted or kept
                after collecting them.

        Raises:
            RuntimeError: If the connection closes before the transfer
                completes, the robot reports an error, or an unexpected
                message type is received.
        """
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

    async def delete_logs(self, session_id: str, hosts: List[str]) -> Dict[str, Any]:
        """Delete logs for an experiment session on the pis.

        Args:
            session_id: The id of the current experiment session, can be set
                to anything at experiment creation.
            hosts: A list of the hostnames of the target pis, should be left
                empty to target all robots.

        Returns:
            A dict containing the responses from the pis, keyed by
            hostname.
        """
        return await self.broadcast(
            {
                "type": "delete_logs",
                "session_id": session_id,
                "hosts": hosts,
            }
        )
    
    async def identify(self, hostname: str) -> None:
        """Make the Thymio associated with the hostname light up red.

        Args:
            hostname: The hostname of the target pi.

        Raises:
            RuntimeError: If any robot's response indicates an error
                (raised by ``_check_results``).
        """
        responses = await self.broadcast({
            "type": "identify",
            "hostname": hostname,
        })
        self._check_results(
            f"Identify '{hostname}'",
            responses,
        )

    def _check_results(self, action: str, responses: Dict[str, Any]) -> None:
        """Check the responses from the pis for errors.

        Args:
            action: What action was attempted, used in the error message.
            responses: The response from every pi, keyed by hostname.

        Raises:
            RuntimeError: If any robot's response has type "error", listing
                all such failures.
        """
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
        
    async def start_tracking(self, config: Dict[str, Any]) -> None:
        """Start the Optitrack tracker and the background loop that broadcasts poses.

        Does nothing if a tracker is already active. Otherwise constructs
        an OptitrackClient from the given config, connects it, and
        schedules ``tracking_loop`` as a background task.

        Args:
            config: The configuration of the experiment containing the
                tracking information such as the optitrack IP etc. Expected
                to contain "host" and "hostname_map", and optionally
                "verbose".
        """
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

    async def tracking_loop(self) -> None:
        """Continuously poll the tracker and broadcast pose updates to the robots.

        Every 0.5 seconds, fetches all current poses from ``self.tracker``
        and, if any are available, broadcasts a "tracking_update" message
        containing each pose serialized to a dict. Runs forever, logging
        (but not raising) any exception so a transient failure doesn't stop
        future updates.
        """

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