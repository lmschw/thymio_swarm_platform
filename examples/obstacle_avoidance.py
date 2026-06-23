import asyncio

from swarm_platform.command import RobotCommand
from swarm_platform.controller import Controller 
from swarm_platform import Robot

class ObstacleAvoidance(Controller):

    def __init__(self, threshold=2500, speed=200):

        self.threshold = threshold
        self.speed = speed

    async def step(self, state):

        if max(state.proximity) > self.threshold:

            return RobotCommand(
                left_motor=-self.speed,
                right_motor=self.speed,
                top_led=(32, 0, 0),
            )

        return RobotCommand(
            left_motor=self.speed,
            right_motor=self.speed,
            top_led=(0, 32, 0),
        )
    

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


async def main():

    runner = Runner(
        ObstacleAvoidance()
    )

    await runner.run()


asyncio.run(main())