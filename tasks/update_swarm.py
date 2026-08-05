"""Manual task script: list known robots and broadcast a code-update command to the swarm."""

import asyncio

from swarm_platform.config import COORDINATOR_IP
from swarm_platform.controller.client import SwarmClient


async def main() -> None:
    """Connect to the coordinator, list robots, and broadcast an update_code command.

    Prints the discovered robots, triggers an `update_code` broadcast to the
    whole swarm, and prints any responses returned by the broadcast.
    """

    client = SwarmClient(COORDINATOR_IP)

    robots = await client.list_robots()

    print(f"Found {len(robots)} robot(s)")

    for robot_id, robot in robots.items():
        print(f" - {robot_id} @ {robot['ip']}")

    print("\nUpdating swarm...\n")

    results = await client.broadcast({
        "type": "update_code"
    })

    print("\nUpdate complete\n")

    # Optional: show responses if your broadcast returns them
    if results:
        for r in results:
            print(r)


if __name__ == "__main__":
    asyncio.run(main())