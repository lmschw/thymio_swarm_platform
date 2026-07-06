import asyncio


class LightLEDsRed:

    name = "light_leds_red"

    def __init__(self, robot, config=None, logger=None):
        self.robot = robot
        self.config = config or {}
        self.logger = logger

        self.running = True
        self.paused = False

    async def run(self):
        print(">>> LIGHT LEDS RED STARTED <<<", flush=True)
        await self.robot.top_led(32, 0, 0)
        await self.robot.stop()
        if self.logger:
            self.logger.log(
                state={"leds": [32, 0, 0]}
            )  

    async def pause(self):
        self.paused = True

    async def resume(self):
        self.paused = False

    async def stop(self):
        self.running = False