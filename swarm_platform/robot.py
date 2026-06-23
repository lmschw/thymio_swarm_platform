from .thymio import ThymioConnection
from .motors import Motors
from .leds import LEDs
from .sensors import Sensors


class Robot:

    def __init__(self):

        self.connection = ThymioConnection()

        self.motors = Motors(self.connection)
        self.leds = LEDs(self.connection)
        self.sensors = Sensors(self.connection)

    async def connect(self):
        await self.connection.connect()

    async def disconnect(self):
        await self.connection.disconnect()