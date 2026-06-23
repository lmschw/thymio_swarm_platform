import asyncio

from swarm_platform.command import RobotCommand
from swarm_platform.controller import Controller 
from swarm_platform.runner import Runner

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

async def main():
    runner = Runner(
        ObstacleAvoidance()
    )
    await runner.run()

asyncio.run(main())