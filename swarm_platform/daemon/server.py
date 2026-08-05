import asyncio
import socket
import json
import os
import subprocess
from pathlib import Path
import base64
import io
import zipfile
import shutil
from typing import Any, Dict, Optional

from swarm_platform.config import COORDINATOR_IP, COORDINATOR_PORT
from swarm_platform.protocol.codec import encode, decode
from swarm_platform.robot.robot import Robot
from swarm_platform.projects.manager import ProjectManager
from swarm_platform.daemon.logger import SessionLogger
from swarm_platform.daemon.log_manager import LogManager
from swarm_platform.tracking.pose import Pose

class SwarmDaemon:
    """Runs on each robot's Raspberry Pi to manage the local robot, its active project, and experiments.

    Maintains a persistent TCP server that the coordinator/controller talks
    to, periodically registers itself with the coordinator and sends
    heartbeats, dispatches incoming JSON messages to the appropriate action
    (starting/stopping experiments, cloning/updating/activating projects,
    identifying the robot, forwarding tracking updates, and streaming
    collected logs back to the caller).
    """

    def __init__(self) -> None:
        """Initialize the daemon, its project manager, robot handle, and internal state.

        Reads the coordinator address and port from
        ``swarm_platform.config`` (itself overridable via the
        ``SWARM_COORDINATOR``/``SWARM_COORDINATOR_PORT`` environment
        variables), sets up the active project manager, the robot handle,
        the log manager, and all of the mutable state used to track the
        currently running experiment.
        """
        print("cwd =", Path.cwd(), flush=True)
        print("__file__ =", __file__, flush=True)
        print("git root =", Path(__file__).resolve().parents[2], flush=True)

        self.coordinator_ip = COORDINATOR_IP
        self.coordinator_port = COORDINATOR_PORT

        self.project_manager = ProjectManager(
            Path("active_project")
        )

        self.robot = Robot(tracker=self)
        self.experiment = None
        self.experiment_task = None
        self.running_experiment = False
        self.active_session = None
        self.log_manager = LogManager()
        self.logger = None
        self.global_poses = {}
        self._restart_requested = False

    async def handle(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch an incoming message to the corresponding daemon action.

        Filters out messages addressed to other hosts, checks that the
        message's session_id (if any) matches the currently active session
        (except for "start_experiment", which establishes the active
        session), and then executes the action matching the message's
        "type" field: ping/status queries, pause/resume/stop of the running
        experiment, starting a new experiment, cloning/updating/activating
        the active project, updating the daemon's own code, deleting logs,
        identifying the robot via its LED, and applying tracking updates.

        Args:
            msg: The decoded message dict. Must contain a "type" key and may
                contain "hosts" and "session_id" keys along with type-specific
                fields.

        Returns:
            A response dict describing the result of the action, or an
            "unknown_command"/"Not applicable" error dict if the message
            could not be handled.
        """
        t = msg.get("type")
        hosts = msg.get("hosts")
        if hosts and len(hosts) > 0 and socket.gethostname() not in hosts:
            print("not in hosts")
            return {"type": "Not applicable"}
        else:
            print(msg, flush=True)
            print(f"[DAEMON] handling message: {t}", flush=True)

        session_id = msg.get("session_id")

        if t != "start_experiment" and session_id and session_id != self.active_session:
            return {"type": "Not applicable"}

        if t == "ping":
            return {"type": "pong"}

        if t == "status":
            return {
                "type": "status",
                "running": self.running_experiment,
            }
        
        if t in ["pause", "resume", "stop"]:
            session_id = msg.get("session_id")
            print(f"[SESSION {session_id}] {t}")
        
        if t == "pause":
            if self.experiment:
                await self.experiment.pause()
            return {"type": "paused"}

        if t == "resume":
            if self.experiment:
                await self.experiment.resume()
            return {"type": "resumed"}

        if t == "stop":
            self.running_experiment = False

            if self.experiment:
                await self.experiment.stop()
            else:
                print("no experiment to stop")

            # if self.experiment_task:
            #     try:
            #         await self.experiment_task
            #     except asyncio.CancelledError:
            #         pass

            await self.robot.stop()
            await self.robot.top_led(0, 0, 0)

            self.experiment = None
            self.experiment_task = None

            return {"type": "stopped"}

        if t == "start_experiment":
            try:
                session_id = msg["session_id"]
                print(f"[SESSION {session_id}] start {msg['name']}", flush=True)
                self.active_session = session_id
                path = self.log_manager.robot_log(
                    session_id,
                    socket.gethostname(),
                )
                self.logger = SessionLogger(path)
                return await self._start_experiment(msg)
            except Exception as e:
                return {
                    "type": "error",
                    "error": str(e),
                }

        if t == "clone_project":
            self.project_manager.clone(
                msg["repository"]
            )
            return {
                "type": "project_cloned"
            }
        
        if t == "update_project":
            self.project_manager.update()
            self._restart_requested = True
            return {
                "type": "project_updated"
            }

        if t == "activate_project":
            self.project_manager.activate()
            return {
                "type": "project_activated"
            }
            
        if t == "update_code":
            subprocess.run("git restore .", shell=True, check=True) # remove all local changes
            subprocess.run('sudo date -s "$(wget -qSO- --max-redirect=0 google.com 2>&1 | grep Date: | cut -d' ' -f5-8)Z"', shell=True, check=True)
            subprocess.run(["git", "pull"], check=True)
            subprocess.run([os.environ["UV_BIN"], "sync"], check=True)
            self._restart_requested = True
            return {
                "type": "code_updated"
            }
        
        if t == "delete_logs":
            try:
                self.log_manager.delete(msg["session_id"])
                return {
                    "type": "deleted",
                }
            except Exception as e:
                return {
                    "type": "error",
                    "error": str(e),
                }

        if t == "identify":
            hostname = msg["hostname"]
            if hostname is not None and socket.gethostname() == hostname:
                await self.robot.top_led(32, 0, 0)
            else:
                await self.robot.top_led(0, 0, 0)
            return {
                "type": "identified"
            }
        
        if t == "tracking_update":

            self.robot.global_poses = {
                hostname: Pose(
                    position=tuple(data["position"]),
                    orientation=tuple(data["orientation"]),
                )
                for hostname, data in msg["poses"].items()
            }

            return {
                "type": "tracking_updated"
            }

        print(f"[DAEMON] unknown message type: {t}", flush=True)
        return {"type": "error", "error": "unknown_command"}

    # ---------------------------
    # EXPERIMENT CONTROL
    # ---------------------------

    async def _run_experiment(self) -> None:
        """Run the current experiment to completion and clean up afterwards.

        Awaits ``self.experiment.run()``, catching and logging any exception
        it raises so the daemon keeps running. Once the experiment finishes
        (or crashes), marks the experiment as no longer running and closes
        the session logger if one is open.
        """
        try:
            print(">>> EXPERIMENT TASK STARTED <<<", flush=True)
            await self.experiment.run()
        except Exception as e:
            print(f">>> EXPERIMENT CRASHED: {repr(e)}")

        finally:
            self.running_experiment = False
            if self.logger is not None:
                self.logger.close()
                self.logger = None

    async def _start_experiment(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Instantiate and launch the requested experiment as a background task.

        Looks up the experiment class from the active project's
        configuration, constructs it with the current robot, the requested
        config, and the session logger, then schedules it to run via
        ``_run_experiment`` on a new asyncio task.

        Args:
            msg: The "start_experiment" message dict. Must contain a "name"
                key identifying the experiment to run and may contain a
                "config" dict of experiment-specific settings.

        Returns:
            {"type": "error", "error": ...} if an experiment is already
            running, otherwise {"type": "started"} once the experiment task
            has been scheduled.
        """
        if self.running_experiment:
            return {
                "type": "error",
                "error": "Experiment already running",
            }

        name = msg["name"]
        config = msg.get(
            "config",
            {}
        )

        experiment_cfg = (
            self.project_manager
            .project
            .experiment_config(name)
        )

        experiment_cls = experiment_cfg.cls

        self.experiment = experiment_cls(
            robot=self.robot,
            config=config,
            logger=self.logger,
        )

        self.running_experiment = True

        self.experiment_task = asyncio.create_task(
            self._run_experiment()
        )

        return {"type": "started"}

    # ---------------------------
    # NETWORK LOOP TASKS
    # ---------------------------

    async def register_loop(self) -> None:
        """Periodically re-register this robot with the coordinator.

        Calls ``register()`` every 30 seconds forever, logging (but not
        raising) any exception so a temporary network failure doesn't stop
        future attempts.
        """
        while True:
            try:
                await self.register()
            except Exception as e:
                print(f"[REGISTER ERROR] {e}")

            await asyncio.sleep(30)

    async def heartbeat_loop(self) -> None:
        """Periodically send a heartbeat to the coordinator.

        Calls ``send_heartbeat()`` every 5 seconds forever, logging (but not
        raising) any exception so a temporary network failure doesn't stop
        future attempts.
        """
        while True:
            try:
                await self.send_heartbeat()
            except Exception as e:
                print(f"[HEARTBEAT ERROR] {e}")

            await asyncio.sleep(5)

    # ---------------------------
    # ROBOT / COORDINATOR
    # ---------------------------

    async def connect_robot(self) -> None:
        """Repeatedly attempt to connect to the robot until it succeeds.

        Retries ``self.robot.connect()`` every 2 seconds, logging each
        failure, until a connection attempt succeeds.
        """
        while True:
            try:
                await self.robot.connect()
                print("[ROBOT] connected")
                break
            except Exception as e:
                print(f"[ROBOT] waiting: {e}")
                await asyncio.sleep(2)

    def get_ip(self) -> str:
        """Determine this machine's outbound IP address.

        Opens a UDP socket "connected" to a public address (8.8.8.8:80)
        without sending any data, purely to let the OS pick the local
        interface/address that would be used to reach it.

        Returns:
            The local IP address as a string.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]

    async def register(self) -> None:
        """Send a one-shot "register" message to the coordinator.

        Opens a new TCP connection to the coordinator and sends this
        robot's hostname, IP address, and port as a "register" message,
        then closes the connection.
        """
        msg = {
            "type": "register",
            "robot_id": socket.gethostname(),
            "ip": self.get_ip(),
            "port": 9000,
        }

        reader, writer = await asyncio.open_connection(
            self.coordinator_ip,
            self.coordinator_port
        )

        writer.write((json.dumps(msg) + "\n").encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    async def send_heartbeat(self) -> None:
        """Send a one-shot "heartbeat" message to the coordinator.

        Opens a new TCP connection to the coordinator and sends this
        robot's hostname as a "heartbeat" message, then closes the
        connection.
        """
        msg = {
            "type": "heartbeat",
            "robot_id": socket.gethostname()
        }

        reader, writer = await asyncio.open_connection(
            self.coordinator_ip,
            self.coordinator_port
        )

        writer.write((json.dumps(msg) + "\n").encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    # ---------------------------
    # TCP SERVER
    # ---------------------------

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Serve a single incoming TCP connection for its whole lifetime.

        Reads newline-delimited JSON messages from the connection in a
        loop. "collect_logs" messages are handled specially by streaming
        the logs back via ``stream_logs``; all other messages are
        dispatched through ``handle`` and the resulting response is encoded
        and written back. If handling a message raises, an "internal_error"
        response is sent instead and the exception is logged. If
        ``self._restart_requested`` was set (e.g. after a project/code
        update), the process exits after responding. The loop ends, and the
        connection is closed, once the peer disconnects.

        Args:
            reader: The stream to read incoming messages from.
            writer: The stream to write responses to.
        """
        while True:
            data = await reader.readline()

            if not data:
                break

            msg = decode(data.decode())

            try:
                if msg.get("type") == "collect_logs":
                    await self.stream_logs(
                        writer,
                        msg["session_id"],
                        delete=msg.get("delete", False),
                    )
                    continue

                response = await self.handle(msg)

                writer.write(
                    (encode(response) + "\n").encode()
                )
                await writer.drain()

                if self._restart_requested:
                    os._exit(0)

            except Exception:
                import traceback
                traceback.print_exc()

                error = {
                    "type": "error",
                    "error": "internal_error",
                }

                writer.write(
                    (encode(error) + "\n").encode()
                )
                await writer.drain()

        writer.close()
        await writer.wait_closed()

    # ---------------------------
    # MAIN RUN LOOP
    # ---------------------------

    async def run(self, host: str = "0.0.0.0", port: int = 9000) -> None:
        """Start the daemon: connect to the robot, run the TCP server, and background loops.

        Blocks until the robot connection succeeds, then starts the TCP
        server that handles incoming connections via
        ``_handle_connection``, launches the registration and heartbeat
        background loops, and finally waits forever (the daemon is expected
        to run until the process is killed or restarted).

        Args:
            host: The address to bind the TCP server to.
            port: The port to bind the TCP server to.
        """
        print(">>> DAEMON STARTED <<<")

        await self.connect_robot()

        server = await asyncio.start_server(
            self._handle_connection,
            host,
            port,
        )

        print("TCP server started")

        asyncio.create_task(self.register_loop())
        asyncio.create_task(self.heartbeat_loop())

        async with server:
            await asyncio.Event().wait()


    async def collect_logs(
        self,
        session_id: str,
        delete: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Zip up the log directory for a session and return it as bytes.

        Args:
            session_id: The id of the experiment session whose logs to
                collect.
            delete: If True, delete the session's log directory after
                zipping it.

        Returns:
            None if the session's log directory does not exist, otherwise a
            dict with "type", a "filename" of "<hostname>.zip", and the zip
            archive's raw bytes under "data".
        """
        print("Collecting logs.")
        log_dir = Path("logs") / session_id

        if not log_dir.exists():
            return None

        buffer = io.BytesIO()

        with zipfile.ZipFile(
            buffer,
            "w",
            zipfile.ZIP_DEFLATED,
        ) as z:
            for file in log_dir.rglob("*"):
                if file.is_file():
                    z.write(
                        file,
                        file.relative_to(log_dir),
                    )

        if delete:
            shutil.rmtree(log_dir)

        return {
            "type": "logs",
            "filename": f"{socket.gethostname()}.zip",
            "data": buffer.getvalue(),   # <-- bytes
        }

    async def stream_logs(
        self,
        writer: asyncio.StreamWriter,
        session_id: str,
        delete: bool = False,
    ) -> None:
        """Collect a session's logs and stream them to the peer in base64-encoded chunks.

        Calls ``collect_logs`` and writes the result to ``writer`` as a
        sequence of newline-delimited JSON messages: a "logs_begin" message
        with the filename/size/chunk count (size 0 and filename None if
        there are no logs), followed by one "logs_chunk" message per 32KB
        chunk of the zip data (base64-encoded), followed by a "logs_end"
        message.

        Args:
            writer: The stream to write the log messages to.
            session_id: The id of the experiment session whose logs to
                stream.
            delete: If True, delete the session's log directory after
                collecting it.
        """
        result = await self.collect_logs(
            session_id,
            delete=delete,
        )

        if result is None:
            writer.write(
                (
                    encode({
                        "type": "logs_begin",
                        "filename": None,
                        "size": 0,
                        "chunks": 0,
                    })
                    + "\n"
                ).encode()
            )
            await writer.drain()

            writer.write(
                (
                    encode({
                        "type": "logs_end"
                    })
                    + "\n"
                ).encode()
            )
            await writer.drain()

            return

        filename = result["filename"]
        data = result["data"]   # <-- bytes

        CHUNK_SIZE = 32 * 1024

        num_chunks = (
            len(data) + CHUNK_SIZE - 1
        ) // CHUNK_SIZE

        writer.write(
            (
                encode({
                    "type": "logs_begin",
                    "filename": filename,
                    "size": len(data),
                    "chunks": num_chunks,
                })
                + "\n"
            ).encode()
        )
        await writer.drain()

        for index in range(num_chunks):
            start = index * CHUNK_SIZE
            end = start + CHUNK_SIZE

            chunk = data[start:end]

            print(
                "[STREAM DEBUG]",
                type(data),
                type(chunk),
                repr(chunk[:20]),
                flush=True,
            )

            writer.write(
                (
                    encode({
                        "type": "logs_chunk",
                        "index": index,
                        "data": base64.b64encode(chunk).decode(),
                    })
                    + "\n"
                ).encode()
            )

            await writer.drain()

        writer.write(
            (
                encode({
                    "type": "logs_end",
                })
                + "\n"
            ).encode()
        )

        await writer.drain()