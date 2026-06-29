import asyncio

from .thymio import ThymioConnection
from .state import RobotState
from .command import RobotCommand
from .config import RobotConfig

class Robot:

    def __init__(self, config: RobotConfig | None = None):
        self.config = config or RobotConfig()
        self.connection = ThymioConnection()

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


    # Motors
    async def drive(self, left: int, right: int):

        await self.connection.node.set_variables({
            "motor.left.target": [int(left)],
            "motor.right.target": [int(right)],
        })

    async def stop(self):
        await self.drive(0, 0)

    # LEDs
    async def top_led(self, r: int, g: int, b: int):

        await self.connection.node.set_variables({
            "leds.top": [int(r), int(g), int(b)]
        })

    # Sensors
    async def proximity(self):
        return await self.connection.read_prox_horizontal()

    async def ground(self):
        return list(self.connection.node["prox.ground.delta"])

    async def buttons(self):

        return {
            "forward": self.connection.node["button.forward"],
            "backward": self.connection.node["button.backward"],
            "left": self.connection.node["button.left"],
            "right": self.connection.node["button.right"],
            "center": self.connection.node["button.center"],
        }

    async def accelerometer(self):

        return list(self.connection.node["acc"])

    async def temperature(self):

        return self.connection.node["temperature"]
    
    async def state(self):
        return RobotState(
            proximity=await self.connection.read_prox_horizontal(),
            ground=list(self.connection.node["prox.ground.delta"]),
            accelerometer=list(self.connection.node["acc"]),
            buttons={
                "forward": bool(self.connection.node["button.forward"]),
                "backward": bool(self.connection.node["button.backward"]),
                "left": bool(self.connection.node["button.left"]),
                "right": bool(self.connection.node["button.right"]),
                "center": bool(self.connection.node["button.center"]),
            },
            temperature=self.connection.node["temperature"],
        )
    
    async def apply(self, command: RobotCommand):
        await self.drive(
            command.left_motor,
            command.right_motor,
        )

        await self.top_led(*command.top_led)