import asyncio
import socket
import json
import asyncio

from swarm_platform.protocol.codec import encode, decode
from swarm_platform.protocol.messages import Ping, Status, Stop, StartExperiment
from swarm_platform.robot.robot import Robot
from swarm_platform.controllers.experiments import EXPERIMENTS

class SwarmDaemon:

    REGISTRY_IP = "10.15.2.96"
    REGISTRY_PORT = 9100

    def __init__(self):
        self.robot = Robot()
        self.experiment = None
        self.running_experiment = False

    async def init(self):
        await self.robot.connect()
        await self.register()

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
            return await self._start_experiment(msg)

        return {"type": "error", "error": "unknown_command"}
    
    async def _start_experiment(self, msg):
        name = msg["name"]
        config = msg.get("config", {})

        self.running_experiment = True

        experiment_cls = self._load_experiment(name)
        self.experiment = experiment_cls(config=config, robot=self.robot)

        await self.experiment.run()

        self.running_experiment = False

        return {"type": "started"}
    
    def _load_experiment(self, name: str):
        if name not in EXPERIMENTS:
            raise ValueError(f"Unknown experiment: {name}")

        return EXPERIMENTS[name]
    
    async def run(self, host="0.0.0.0", port=9000):

        await self.init()

        async def announcer():
            while True:
                self.broadcast_announce()
                await asyncio.sleep(2)

        asyncio.create_task(announcer())

        server = await asyncio.start_server(self._handle_connection, host, port)

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


    def get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]


    async def register(self):

        msg = {
            "type": "register",
            "id": socket.gethostname(),
            "ip": get_ip(),
            "port": 9000
        }

        reader, writer = await asyncio.open_connection(
            REGISTRY_IP,
            REGISTRY_PORT
        )

        writer.write((json.dumps(msg) + "\n").encode())
        await writer.drain()

        writer.close()
        await writer.wait_closed()