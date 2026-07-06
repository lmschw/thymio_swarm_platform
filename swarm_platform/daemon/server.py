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

from swarm_platform.protocol.codec import encode, decode
from swarm_platform.robot.robot import Robot
from swarm_platform.projects.manager import ProjectManager
from swarm_platform.daemon.logger import SessionLogger
from swarm_platform.daemon.log_manager import LogManager

class SwarmDaemon:

    def __init__(self):
        self.coordinator_ip = os.getenv("SWARM_COORDINATOR", "10.15.2.63")
        self.coordinator_port = int(os.getenv("SWARM_COORDINATOR_PORT", "9100"))

        self.project_manager = ProjectManager(
            Path("example_project")
        )

        self.robot = Robot()
        self.experiment = None
        self.experiment_task = None
        self.running_experiment = False
        self.active_session = None
        self.log_manager = LogManager()
        self.logger = None

    # ---------------------------
    # MESSAGE HANDLING
    # ---------------------------

    async def handle(self, msg: dict):
        t = msg.get("type")
        print(f"[DAEMON] handling message: {t}", flush=True)

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

            if self.experiment_task:
                try:
                    await self.experiment_task
                except asyncio.CancelledError:
                    pass

            await self.robot.stop()
            await self.robot.top_led(0, 0, 0)

            self.experiment = None
            self.experiment_task = None

            return {"type": "stopped"}

        if t == "start_experiment":
            session_id = msg.get("session_id")
            print(f"[SESSION {session_id}] start {msg['name']}", flush=True)
            path = self.log_manager.robot_log(
                msg["session_id"],
                socket.gethostname(),
            )

            self.logger = SessionLogger(path)
            print("[DAEMON] logger created ->", self.logger, flush=True)
            return await self._start_experiment(msg)

        if t == "update_code":
            try:
                self.running_experiment = False
                if self.experiment_task:
                    self.experiment_task.cancel()
                
                subprocess.run(["git", "pull"], check=True)
                uv = os.environ["UV_BIN"]
                subprocess.run([uv, "sync"], check=True)
                print("Update successful", flush=True)
                os._exit(0)
            except Exception:
                import traceback
                traceback.print_exc()
                raise

        if t == "activate_project":
            path = msg["path"]
            print(f"[PROJECT] Activating: {path}", flush=True)
            self.project_manager.activate(path)

            # stop running experiment on switch
            self.running_experiment = False

            if self.experiment:
                await self.robot.stop()
                await self.robot.top_led(0, 0, 0)

            return {"type": "project_activated"}

        if t == "collect_logs":
            return await self.collect_logs(
                msg["session_id"],
                delete=msg.get("delete", False),
            )
        
        if t == "delete_log":
            self.log_manager.delete(
                msg["session_id"]
            )

            return {
                "type": "deleted",
            }

        print(f"[DAEMON] unknown message type: {t}", flush=True)
        return {"type": "error", "error": "unknown_command"}

    # ---------------------------
    # EXPERIMENT CONTROL
    # ---------------------------

    async def _run_experiment(self):
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

    async def _start_experiment(self, msg):
        if self.running_experiment:
            print("already running")
            return {"type": "error", "error": "Experiment already running"}

        name = msg["name"]
        config = msg.get("config", {})
        experiment_cls = self.project_manager.experiment(name)

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

    async def register_loop(self):
        while True:
            try:
                await self.register()
            except Exception as e:
                print(f"[REGISTER ERROR] {e}")

            await asyncio.sleep(30)

    async def heartbeat_loop(self):
        while True:
            try:
                await self.send_heartbeat()
            except Exception as e:
                print(f"[HEARTBEAT ERROR] {e}")

            await asyncio.sleep(5)

    # ---------------------------
    # ROBOT / COORDINATOR
    # ---------------------------

    async def connect_robot(self):
        while True:
            try:
                await self.robot.connect()
                print("[ROBOT] connected")
                break
            except Exception as e:
                print(f"[ROBOT] waiting: {e}")
                await asyncio.sleep(2)

    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]

    async def register(self):
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

    async def send_heartbeat(self):
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

    async def _handle_connection(self, reader, writer):
        while True:
            data = await reader.readline()
            if not data:
                break

            msg = decode(data.decode())

            try:
                response = await self.handle(msg)
            except Exception:
                import traceback
                traceback.print_exc()

                response = {
                    "type": "error",
                    "error": "internal_error",
                }

            writer.write((encode(response) + "\n").encode())
            await writer.drain()

        writer.close()
        await writer.wait_closed()

    # ---------------------------
    # MAIN RUN LOOP
    # ---------------------------

    async def run(self, host="0.0.0.0", port=9000):
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


    async def collect_logs(self, session_id, delete=False):
        log_dir = Path("logs") / session_id

        print(f"[COLLECT LOGS] session_id={session_id} log_dir={log_dir} delete={delete}")

        if not log_dir.exists():
            print(f"[COLLECT LOGS] log_dir does not exist: {log_dir}")
            return {
                "type": "logs",
                "content": None,
            }

        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
            for file in log_dir.rglob("*"):
                if file.is_file():
                    z.write(file, file.relative_to(log_dir))

        if delete:
            shutil.rmtree(log_dir)

        return {
            "type": "logs",
            "filename": f"{session_id}.zip",
            "content": base64.b64encode(
                buffer.getvalue()
            ).decode(),
        }