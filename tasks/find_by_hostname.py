"""Manual task script: make a specific robot identify itself (e.g. by hostname)."""

import asyncio
import sys

from swarm_platform.config import COORDINATOR_IP
from swarm_platform.controller.client import SwarmClient


async def main() -> None:
    """Parse the target hostname from argv and ask the coordinator to identify that robot.

    Prints usage and returns early if the expected single hostname argument is
    not provided.
    """

    if len(sys.argv) != 2:
        print("Usage:")
        print("    python ./tasks/find_by_hostname.py thymio-03")
        return

    client = SwarmClient(COORDINATOR_IP)

    await client.identify(sys.argv[1])

asyncio.run(main())