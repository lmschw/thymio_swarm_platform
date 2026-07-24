import asyncio
import socket

from .connection import ThymioConnection
from .state import RobotState
from ..protocol.command import RobotCommand
from ..utils.config import RobotConfig

class Robot:

    def __init__(self, config: RobotConfig | None = None, tracker=None):
        self.config = config or RobotConfig()
        self.connection = ThymioConnection()
        self.hostname = socket.gethostname()
        self.tracker = tracker
        self.global_poses = {}

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

    async def disconnect(self):
        await self.connection.disconnect()

    async def _set_variables(self, var_dict, timeout=1.0):
        try:
            await asyncio.wait_for(
                self.connection.node.set_variables(var_dict),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Timed out waiting for ack on set_variables({var_dict})"
            )

    # Motors
    async def drive(self, left: int, right: int):

        await self._set_variables({
            "motor.left.target": [int(left)],
            "motor.right.target": [int(right)],
        })

    async def stop(self):
        await self.drive(0, 0)

    # LEDs
    async def top_led(self, r: int, g: int, b: int):
        await self._set_variables({
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

    async def send(self, value):
        await self._set_variables({
            "prox.comm.tx": [int(value)]
        })

        print(
            "TX set to",
            self.connection.node.var.get("prox.comm.tx"),
        )

    async def receive(self):
        await self.connection.process_messages()
        rx = self.connection.node.var.get("prox.comm.rx")
        print("RX =", rx)
        print("rx intensities", self.connection.node.var.get("prox.comm.rx._intensities"))
        print("prox", self.connection.node.var.get("prox.horizontal"))
        return rx
    
    async def get_global_pose(self):
        poses = self.global_poses
        return poses.get(self.hostname)

    async def get_all_global_poses(self):
        return dict(
            self.global_poses
        )