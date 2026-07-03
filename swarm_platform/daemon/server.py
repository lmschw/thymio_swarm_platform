import asyncio
import socket
import json
import os
import subprocess
from pathlib import Path

from swarm_platform.protocol.codec import encode, decode
from swarm_platform.robot.robot import Robot
from swarm_platform.projects.manager import ProjectManager
from swarm_platform.daemon.logger import SessionLogger

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

    # ---------------------------
    # MESSAGE HANDLING
    # ---------------------------

    async def handle(self, msg: dict):
        t = msg.get("type")
        session_id = msg.get("session_id")
        print(f"[SESSION {session_id}] {t}")

        if session_id != self.active_session:
            return {
                "type": "error",
                "error": "wrong_session",
            }

        if t == "ping":
            return {"type": "pong"}

        if t == "status":
            return {
                "type": "status",
                "running": self.running_experiment,
            }
        
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
            self.active_session = session_id
            print(f"[SESSION {session_id}] start {msg['name']}", flush=True)
            self.logger = SessionLogger(
                session_id=msg.get("session_id", "no-session"),
                robot_id=socket.gethostname(),
            )
            print("[DAEMON] logger created ->", self.logger, flush=True)
            return await self._start_experiment(msg)

        if t == "update_code":
            subprocess.run(["git", "pull"], check=True)
            subprocess.run(["uv", "sync"], check=True)

            # tell systemd to restart safely
            return {"type": "updated_restart_required"}
        
        if t == "updated_restart_required":
            self.running_experiment = False
            self.experiment_task.cancel()

            # exit process cleanly
            os._exit(0)

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

        return {"type": "error", "error": "unknown_command"}

    # ---------------------------
    # EXPERIMENT CONTROL
    # ---------------------------

    async def _run_experiment(self):
        try:
            print(">>> EXPERIMENT TASK STARTED <<<", flush=True)
            await asyncio.sleep(2)
            print(">>> EXPERIMENT STILL RUNNING <<<", flush=True)
            await self.experiment.run()

            print(">>> EXPERIMENT FINISHED <<<")

        except Exception as e:
            print(f">>> EXPERIMENT CRASHED: {repr(e)}")

        finally:
            self.running_experiment = False

    async def _start_experiment(self, msg):
        print(f"Loading experiment msg: {msg}")

        if self.running_experiment:
            return {"type": "error", "error": "Experiment already running"}
        
        name = msg["name"]
        config = msg.get("config", {})
        
        print(f"Loading experiment: {name}")
        print("Starting experiment now...")

        experiment_cls = self.project_manager.experiment(name)  

        self.experiment = experiment_cls(
            config=config,
            robot=self.robot,
            logger=self.logger,
        )

        print("[DAEMON EXPERIMENT CLASS]", experiment_cls, flush=True)


        self.running_experiment = True

        self.experiment_task = asyncio.create_task(self.experiment.run())

        print(f"[DAEMON] experiment task started: {self.experiment_task}")

        self.experiment_task.add_done_callback(
            lambda t: print(f"[EXPERIMENT DONE] {t.exception()}")
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
            except Exception as e:
                response = {"type": "error", "error": str(e)}

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