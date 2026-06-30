import asyncio

from ..robot.robot import Robot
from ..utils.config import RobotConfig

class Experiment:

    def __init__(self, controller, logger=None, config: RobotConfig | None = None):
        self.controller = controller
        self.logger = logger
        self.config = config or RobotConfig()
        self.robot = Robot(self.config)

    async def run(self, duration=None):
        dt = 1.0 / self.config.control_frequency
        async with self.robot:
            if self.logger:
                self.logger.start()
            await self.controller.setup(self.robot)
            start_time = asyncio.get_event_loop().time()
            try:
                while True:
                    if duration is not None:
                        if asyncio.get_event_loop().time() - start_time > duration:
                            break
                    state = await self.robot.state()
                    command = await self.controller.step(state)
                    await self.robot.apply(command)
                    if self.logger:
                        self.logger.log(state, command)
                    await asyncio.sleep(dt)
            finally:
                await self.controller.cleanup(self.robot)
                if self.logger:
                    self.logger.stop()