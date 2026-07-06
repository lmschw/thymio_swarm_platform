import asyncio


class ObstacleAvoidance:

    name = "obstacle_avoidance"

    FORWARD_SPEED = 200
    TURN_SPEED = 150
    THRESHOLD = 1800

    def __init__(self, robot, config=None, logger=None):
        self.robot = robot
        self.config = config or {}
        self.logger = logger 

        self.running = True
        self.paused = False

    async def run(self):
        print("OBSTACLE AVOIDANCE STARTED", flush=True)
        
        try:
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
                        left_speed = -self.TURN_SPEED
                        right_speed = self.TURN_SPEED
                    else:
                        left_speed = self.TURN_SPEED
                        right_speed = -self.TURN_SPEED

                else:
                    await self.robot.top_led(0, 255, 0)
                    left_speed = self.FORWARD_SPEED
                    right_speed = self.FORWARD_SPEED

                await self.robot.drive(left_speed, right_speed)

                if self.logger:
                    self.logger.log(
                        state={"proximity": prox},
                        command={
                            "left": left_speed,
                            "right": right_speed,
                        }
                    )

                await asyncio.sleep(0.05)

        except asyncio.CancelledError:
            print("[EXPERIMENT] Cancelled safely", flush=True)

        finally:
            await self.robot.stop()
            await self.robot.top_led(0, 0, 0)

            if self.logger:
                self.logger.log(
                    state={"event": "shutdown"},
                    command=None
                )

                self.logger.close()

    async def pause(self):
        self.paused = True

    async def resume(self):
        self.paused = False

    async def stop(self):
        self.running = False