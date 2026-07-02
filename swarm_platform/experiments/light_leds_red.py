import asyncio


class LightLEDsRed:

    def __init__(self, robot, config=None):
        self.robot = robot
        self.config = config or {}

        self.running = True
        self.paused = False

    async def run(self):
        print(">>> OBSTACLE AVOIDANCE STARTED <<<", flush=True)

        while self.running:

            if self.paused:
                await self.robot.stop()
                await asyncio.sleep(0.1)
                continue

            await self.robot.top_led(32, 0, 0)

            await asyncio.sleep(0.05)

        await self.robot.stop()
        await self.robot.top_led(0, 0, 0)

    async def pause(self):
        self.paused = True

    async def resume(self):
        self.paused = False

    async def stop(self):
        self.running = False