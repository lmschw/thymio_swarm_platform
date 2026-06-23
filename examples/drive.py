import asyncio

from swarm_platform import Robot


async def main():
    async with Robot() as robot:
        while True:
            prox = await robot.proximity()
            if max(prox) > 2500:
                await robot.drive(-200, 200)
            else:
                await robot.drive(200, 200)

            await asyncio.sleep(0.05)
asyncio.run(main())