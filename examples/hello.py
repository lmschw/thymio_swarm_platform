import asyncio

from swarm_platform import Robot

async def hello():
    robot = Robot()
    await robot.connect()

    print("Connected!")

    await robot.leds.top(0, 32, 0)

    print(await robot.sensors.proximity())

    await asyncio.sleep(5)
    await robot.motors.stop()
    await robot.disconnect()

asyncio.run(hello())