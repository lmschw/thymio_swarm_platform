import asyncio

from swarm_platform.laptop.client import SwarmClient


async def main():

    client = SwarmClient("10.15.2.63")

    robots = await client.list_robots()

    print(f"Found {len(robots)} robots")

    for robot_id, robot in robots.items():
        print(f"  {robot_id}: {robot['ip']}")

    await client.broadcast(
        {
            "type": "start_experiment",
            "name": "light_leds_green",
            "config": {},
        }
    )

    while True:

        cmd = input("[p]ause  [r]esume  [s]top > ").lower()

        if cmd == "p":

            await client.broadcast(
                {
                    "type": "pause",
                }
            )

        elif cmd == "r":

            await client.broadcast(
                {
                    "type": "resume",
                }
            )

        elif cmd == "s":

            await client.broadcast(
                {
                    "type": "stop",
                }
            )

            break


if __name__ == "__main__":
    asyncio.run(main())