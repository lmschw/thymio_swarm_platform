import asyncio

from swarm_platform.controller.client import SwarmClient


async def main():

    client = SwarmClient("10.15.2.63")  # coordinator IP

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