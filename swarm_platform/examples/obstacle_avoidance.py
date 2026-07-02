import asyncio

from swarm_platform.protocol.command import RobotCommand
from swarm_platform.controllers.controller import Controller 
from swarm_platform import Experiment, RobotConfig
from swarm_platform.utils.logging import CSVLogger


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

    experiment = Experiment(
        controller=ObstacleAvoidance(),
        logger=CSVLogger("results/run_001.csv"),
        config=RobotConfig(control_frequency=20),
    )

    await experiment.run(duration=60)


if __name__ == "__main__":
    asyncio.run(main())