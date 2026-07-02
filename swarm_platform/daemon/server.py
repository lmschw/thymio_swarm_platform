import asyncio
import socket
import json
import asyncio
import os
import subprocess

from swarm_platform.protocol.codec import encode, decode
from swarm_platform.protocol.messages import Ping, Status, Stop, StartExperiment
from swarm_platform.robot.robot import Robot
from swarm_platform.controllers.experiments import EXPERIMENTS

class SwarmDaemon:

    def __init__(self):
        self.coordinator_ip = os.getenv("SWARM_COORDINATOR", "10.15.2.63")
        self.coordinator_port = int(os.getenv("SWARM_COORDINATOR_PORT", "9100"))

        if self.coordinator_ip is None:
            raise RuntimeError(
                "SWARM_COORDINATOR not configured."
            )

        self.robot = Robot()
        self.experiment = None
        self.running_experiment = False

    async def handle(self, msg: dict):
        t = msg.get("type")

        if t == "ping":
            return {"type": "pong"}

        if t == "status":
            return {
                "type": "status",
                "running": self.running_experiment,
            }

        if t == "stop":
            self.running_experiment = False
            await self.robot.stop()
            return {"type": "stopped"}

        if t == "start_experiment":
            print("[RAW MSG]", msg)
            return await self._start_experiment(msg)
        
        elif t == "update_code":
            subprocess.run(["git", "pull"])
            subprocess.run(["sudo", "systemctl", "restart", "swarm-daemon"])
            return {"type": "updated"}

        return {"type": "error", "error": "unknown_command"}
    
    async def _run_experiment(self):
        try:
            await self.experiment.run()
        finally:
            self.running_experiment = False
    
    async def _start_experiment(self, msg):
        if self.running_experiment:
            return {
                "type": "error",
                "error": "Experiment already running"
            }

        name = msg["name"]
        config = msg.get("config", {})

        experiment_cls = self._load_experiment(name)
        self.experiment = experiment_cls(config=config, robot=self.robot)

        self.running_experiment = True

        asyncio.create_task(self._run_experiment())

        return {"type": "started"}
    
    def _load_experiment(self, name: str):
        if name not in EXPERIMENTS:
            raise ValueError(f"Unknown experiment: {name}")

        return EXPERIMENTS[name]
    
    async def run(self, host="0.0.0.0", port=9000):
        print(">>> DAEMON STARTED <<<")

        await asyncio.sleep(10)

        print(">>> STILL ALIVE <<<")
        
        while True:
            try:
                await self.robot.connect()
                break
            except Exception as e:
                print(f"Waiting for robot: {e}")
                await asyncio.sleep(2)

        asyncio.create_task(self.coordinator_loop())

        print("Starting TCP server...")

        server = await asyncio.start_server(
            self._handle_connection,
            host,
            port,
        )

        async with server:
            await server.serve_forever()

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


    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]

    async def register(self):
        msg = {
            "type": "register",
            "robot_id": socket.gethostname(),
            "ip": self.get_ip(),
            "port": 9000
        }

        _, writer = await asyncio.open_connection(
            self.coordinator_ip,
            self.coordinator_port
        )

        writer.write((json.dumps(msg) + "\n").encode())
        await writer.drain()

        writer.close()
        await writer.wait_closed()


    async def heartbeat_loop(self):
        while True:
            try:
                await self.register()

                while True:
                    await self.send_heartbeat()
                    await asyncio.sleep(5)

            except Exception as e:
                print(f"Coordinator unavailable: {e}")

            await asyncio.sleep(5)

    async def send_heartbeat(self):
        try:
            msg = {
                "type": "heartbeat",
                "robot_id": socket.gethostname()
            }

            _, writer = await asyncio.open_connection(
                self.coordinator_ip,
                self.coordinator_port
            )

            writer.write((json.dumps(msg) + "\n").encode())
            await writer.drain()

            writer.close()
            await writer.wait_closed()

        except Exception:
            pass

        await asyncio.sleep(5)

    async def coordinator_loop(self):
        while True:
            try:
                await self.register()
                await self.heartbeat_loop()
            except Exception as e:
                print(f"Coordinator unavailable: {e}")

            await asyncio.sleep(5)