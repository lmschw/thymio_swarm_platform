import asyncio
from swarm_platform.laptop.client import SwarmClient

async def main():

    swarm = SwarmClient("10.15.2.63")

    robots = await swarm.list_robots()

    print("Active robots:")
    for rid, r in robots.items():
        print(rid, r)


asyncio.run(main())