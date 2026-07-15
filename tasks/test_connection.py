import asyncio
from swarm_platform.controller.client import SwarmClient
from swarm_platform.controller.utils.utils import print_robots, get_robots

async def main():

    swarm = SwarmClient("10.15.2.63")

    print_robots(await get_robots(swarm))


asyncio.run(main())