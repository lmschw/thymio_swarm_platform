import asyncio

from swarm_platform import Robot


async def hello():

    async with Robot() as robot:

        await robot.top_led(0, 32, 0)

        while True:

            print(await robot.proximity_horizontal())

            await asyncio.sleep(0.05)


asyncio.run(hello())