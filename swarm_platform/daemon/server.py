import asyncio
import socket
import json
import os
import subprocess

from swarm_platform.protocol.codec import encode, decode
from swarm_platform.robot.robot import Robot
from swarm_platform.controllers.experiments import EXPERIMENTS


class SwarmDaemon:

    def __init__(self):
        self.coordinator_ip = os.getenv("SWARM_COORDINATOR", "10.15.2.63")
        self.coordinator_port = int(os.getenv("SWARM_COORDINATOR_PORT", "9100"))

        self.robot = Robot()
        self.experiment = None
        self.running_experiment = False

    # ---------------------------
    # MESSAGE HANDLING
    # ---------------------------

    async def handle(self, msg: dict):
        t = msg.get("type")

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
                self.experiment_task.cancel()

            await self.robot.stop()

            return {"type": "stopped"}

        if t == "start_experiment":
            print("[RAW MSG]", msg)
            return await self._start_experiment(msg)

        if t == "update_code":
            subprocess.run(["git", "pull"])
            subprocess.run(["systemctl", "restart", "swarm-daemon"])
            return {"type": "updated"}

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

        if name not in EXPERIMENTS:
            return {"type": "error", "error": f"Unknown experiment: {name}"}

        experiment_cls = EXPERIMENTS[name]

        self.experiment = experiment_cls(
            robot=self.robot,
            config=config
        )

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