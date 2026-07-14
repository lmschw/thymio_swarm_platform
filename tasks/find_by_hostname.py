import asyncio
import sys

from swarm_platform.controller.client import SwarmClient

async def main():

    if len(sys.argv) != 2:
        print("Usage:")
        print("    python ./tasks/find_by_hostname.py thymio-03")
        return

    client = SwarmClient("10.15.2.63")

    await client.identify(sys.argv[1])

asyncio.run(main())