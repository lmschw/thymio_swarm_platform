import asyncio


class Stop:
    def __init__(self, robot, config=None):
        self.robot = robot
        self.config = config or {}

        self.running = True
        self.paused = False

    async def run(self):
        print(">>> STOPPING <<<", flush=True)

        await self.robot.stop()
        await self.robot.top_led(0, 0, 0)

    async def pause(self):
        self.paused = True

    async def resume(self):
        self.paused = False

    async def stop(self):
        self.running = False