import asyncio
from swarm_platform.controller.client import SwarmClient
from swarm_platform.controller.utils.utils import normalize_robots

COORDINATOR_IP = "10.15.2.63"


async def main():
    client = SwarmClient(COORDINATOR_IP)

    robots_raw = await client.list_robots()
    robots = normalize_robots(robots_raw)

    print(f"\nFound {len(robots)} robots\n")

    for robot_id, robot in robots.items():
        print(f"  {robot_id}: {robot['ip']}:{robot.get('port', 9000)}")

    print("\nStarting obstacle avoidance...\n")

    await client.activate_project("test_project")
    await client.start_experiment("obstacle_avoidance", {})

    while True:

        cmd = input("\n[p]ause  [r]esume  [s]top > ").strip().lower()

        if cmd == "p":
            print("Pausing...")
            await client.broadcast({"type": "pause"})

        elif cmd == "r":
            print("Resuming...")
            await client.broadcast({"type": "resume"})

        elif cmd == "s":
            print("Stopping...")
            await client.broadcast({"type": "stop"})
            break


if __name__ == "__main__":
    asyncio.run(main())