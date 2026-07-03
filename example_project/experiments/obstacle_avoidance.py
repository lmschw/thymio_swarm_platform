import asyncio


class ObstacleAvoidance:

    name = "obstacle_avoidance"

    FORWARD_SPEED = 200
    TURN_SPEED = 150
    THRESHOLD = 1800

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

            prox = await self.robot.proximity_horizontal()

            left = prox[0] + prox[1]
            center = prox[2]
            right = prox[3] + prox[4]

            if center > self.THRESHOLD:

                await self.robot.top_led(255, 255, 0)

                if left < right:
                    await self.robot.drive(-self.TURN_SPEED, self.TURN_SPEED)
                else:
                    await self.robot.drive(self.TURN_SPEED, -self.TURN_SPEED)

            else:
                await self.robot.top_led(0, 255, 0)
                await self.robot.drive(self.FORWARD_SPEED, self.FORWARD_SPEED)

            await asyncio.sleep(0.05)

        await self.robot.stop()
        await self.robot.top_led(0, 0, 0)

    async def pause(self):
        self.paused = True

    async def resume(self):
        self.paused = False

    async def stop(self):
        self.running = False