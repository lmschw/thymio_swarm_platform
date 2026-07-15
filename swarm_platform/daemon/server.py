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
        print("cwd =", Path.cwd(), flush=True)
        print("__file__ =", __file__, flush=True)
        print("git root =", Path(__file__).resolve().parents[2], flush=True)

        self.coordinator_ip = os.getenv("SWARM_COORDINATOR", "10.15.2.63")
        self.coordinator_port = int(os.getenv("SWARM_COORDINATOR_PORT", "9100"))

        self.project_manager = ProjectManager(
            Path("active_project")
        )

        self.robot = Robot()
        self.experiment = None
        self.experiment_task = None
        self.running_experiment = False
        self.active_session = None
        self.log_manager = LogManager()
        self.logger = None

    async def handle(self, msg: dict):
        t = msg.get("type")
        print(f"[DAEMON] handling message: {t}", flush=True)
        print(msg, flush=True)

        hosts = msg.get("hosts")

        print("hosts", hosts)

        if hosts and len(hosts) > 0 and socket.gethostname() not in hosts:
            return {"type": "Not applicable"}

        session_id = msg.get("session_id")
        print("session_id", session_id)

        if session_id and session_id != self.active_session:
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
            print("in stop")
            self.running_experiment = False

            if self.experiment:
                print("experiment stop")
                await self.experiment.stop()
            else:
                print("no experiment to stop")

            # if self.experiment_task:
            #     try:
            #         await self.experiment_task
            #     except asyncio.CancelledError:
            #         pass

            print("robot stop")
            await self.robot.stop()
            print("robot top led off")  
            await self.robot.top_led(0, 0, 0)

            print("setting experiment and task to None")
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
            subprocess.run(["git", "pull"], check=True)
            subprocess.run([os.environ["UV_BIN"], "sync"], check=True)
            self._restart_requested = True
            return {
                "type": "code_updated"
            }
            
        if t == "collect_logs":
            try:
                return await self.collect_logs(
                    msg["session_id"],
                    delete=msg.get("delete", False),
                )
            except Exception as e:
                return {
                    "type": "error",
                    "error": str(e),
                }
        
        if t == "delete_log":
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

            if getattr(self, "_restart_requested", False):
                os._exit(0)

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
