import asyncio
from swarm.client import SwarmClient

async def main():

    swarm = SwarmClient("10.15.2.96")

    robots = await swarm.list_robots()

    print("Active robots:")
    for rid, r in robots.items():
        print(rid, r)


asyncio.run(main())