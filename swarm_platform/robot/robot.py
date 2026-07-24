import asyncio
import socket

from .connection import ThymioConnection
from .state import RobotState
from ..protocol.command import RobotCommand
from ..utils.config import RobotConfig

class Robot:

    def __init__(self, config: RobotConfig | None = None):
        self.config = config or RobotConfig()
        self.connection = ThymioConnection()
        self.tracking = None
        self.hostname = socket.gethostname()

    # Context manager
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            await self.stop()
        finally:
            await self.disconnect()

    
    # Connection
    async def connect(self):
        await self.connection.connect()
        await self.connection.node.set_variables({
            "prox.comm.enable": [1],
        })

    async def disconnect(self):
        await self.connection.disconnect()

    # Motors
    async def drive(self, left: int, right: int):

        await self.connection.node.set_variables({
            "motor.left.target": [int(left)],
            "motor.right.target": [int(right)],
        })

    async def stop(self):
        await self.drive(0, 0)
        self.robot.set_tracking(None)

    # LEDs
    async def top_led(self, r: int, g: int, b: int):
        await self.connection.node.set_variables({
            "leds.top": [int(r), int(g), int(b)]
        })

    # Sensors
    async def proximity_horizontal(self):
        await self.connection.process_messages()
        return list(self.connection.node.var.get("prox.horizontal"))

    async def proximity_ground_delta(self):
        await self.connection.process_messages()
        return list(self.connection.node.var.get("prox.ground.delta"))
    
    async def proximity_ground_reflected(self):
        await self.connection.process_messages()
        return list(self.connection.node.var.get("prox.ground.reflected"))
    
    async def proximity_ground_ambiant(self):
        await self.connection.process_messages()
        return list(self.connection.node.var.get("prox.ground.ambiant"))

    async def buttons(self):
        await self.connection.process_messages()
        return {
            "forward": self.connection.node.var.get("button.forward"),
            "backward": self.connection.node.var.get("button.backward"),
            "left": self.connection.node.var.get("button.left"),
            "right": self.connection.node.var.get("button.right"),
            "center": self.connection.node.var.get("button.center"),
        }

    async def accelerometer(self):
        await self.connection.process_messages()
        return list(self.connection.node.var.get("acc"))

    async def temperature(self):
        await self.connection.process_messages()
        return self.connection.node["temperature"]

    # Sounds
    async def system_sound(self, sound: int):
        if sound != -1:
            print("system.sound", sound)

    async def sound_stop(self):
        await self.system_sound(-1)
    
    async def state(self):
        return RobotState(
            proximity=await self.proximity_horizontal(),
            ground=await self.proximity_ground_delta(),
            accelerometer=await self.accelerometer(),
            buttons=await self.buttons(),
            temperature=await self.temperature(),
        )
    
    async def apply(self, command: RobotCommand):
        await self.drive(
            command.left_motor,
            command.right_motor,
        )

        await self.top_led(*command.top_led)

    async def send(self, value: int):
        await self.connection.node.set_variables({
            "prox.comm.tx": [int(value)]
        })

    async def receive(self):
        await self.connection.process_messages()
        if self.connection.node.var.get("prox.comm.rx") == 0:
            return None
        return int(self.connection.node.var.get("prox.comm.rx"))
    

    # Tracking (Optitrack)
    def set_tracking(self, tracking):
        self.tracking = tracking

    async def global_position(self):
        if self.tracking is None:
            raise RuntimeError(
                "Tracking has not been enabled."
            )
        return await self.tracking.position(self.hostname)
    
    async def all_positions(self):
        if self.tracking is None:
            raise RuntimeError(
                "Tracking is not enabled for this experiment."
            )
        return self.tracking.all_positions()