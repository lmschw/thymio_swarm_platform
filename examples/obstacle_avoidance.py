import asyncio
from swarm_platform.controller import session
from swarm_platform.controller.client import SwarmClient
from swarm_platform.controller.utils.utils import print_robots, get_robots

COORDINATOR_IP = "10.15.2.63"

async def main():
    client = SwarmClient(COORDINATOR_IP)

    print_robots(await get_robots(client))

    print("\nStarting obstacle avoidance...\n")

    session = client.session("run-001")
    await session.activate_project("example_project")
    await session.start("obstacle_avoidance", {})

    while True:

        cmd = input("\n[p]ause  [r]esume  [s]top > ").strip().lower()

        if cmd == "p":
            print("Pausing...")
            await session.pause()

        elif cmd == "r":
            print("Resuming...")
            await session.resume()

        elif cmd == "s":
            print("Stopping...")
            await session.stop()
            break

    await session.collect_logs()

    # await session.collect_logs(delete_remote=False)
    # await session.delete_logs()


if __name__ == "__main__":
    asyncio.run(main())