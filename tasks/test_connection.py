"""Manual task script: connect to the coordinator and print the known robots."""

import asyncio
from swarm_platform.config import COORDINATOR_IP
from swarm_platform.controller.client import SwarmClient
from swarm_platform.controller.utils.utils import print_robots, get_robots


async def main() -> None:
    """Connect to the coordinator and print all currently known robots."""

    swarm = SwarmClient(COORDINATOR_IP)

    print_robots(await get_robots(swarm))


asyncio.run(main())