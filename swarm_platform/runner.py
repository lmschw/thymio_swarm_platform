import asyncio

from swarm_platform import Robot


class Runner:

    def __init__(self, controller, frequency=20):
        self.controller = controller
        self.dt = 1 / frequency

    async def run(self):
        async with Robot() as robot:
            await self.controller.setup(robot)
            try:
                while True:
                    state = await robot.state()
                    command = await self.controller.step(state)
                    await robot.apply(command)
                    await asyncio.sleep(self.dt)
            finally:
                await self.controller.cleanup(robot)