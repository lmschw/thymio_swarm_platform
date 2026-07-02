import asyncio

from swarm_platform.controllers.experiments import Experiment


class ObstacleAvoidance(Experiment):

    FORWARD_SPEED = 200
    TURN_SPEED = 150
    THRESHOLD = 1800

    async def run(self):

        while True:

            prox = await self.robot.proximity_horizontal()

            left = prox[0] + prox[1]
            center = prox[2]
            right = prox[3] + prox[4]

            if center > self.THRESHOLD:

                if left < right:
                    # Turn left
                    await self.robot.top_led(255, 255, 0)   # yellow
                    await self.robot.drive(
                        -self.TURN_SPEED,
                        self.TURN_SPEED,
                    )

                else:
                    # Turn right
                    await self.robot.top_led(255, 255, 0)   # yellow
                    await self.robot.drive(
                        self.TURN_SPEED,
                        -self.TURN_SPEED,
                    )

            else:
                # Drive forward
                await self.robot.top_led(0, 255, 0)         # green
                await self.robot.drive(
                    self.FORWARD_SPEED,
                    self.FORWARD_SPEED,
                )

            await asyncio.sleep(0.05)