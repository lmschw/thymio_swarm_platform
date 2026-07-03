import asyncio
import json
import sys

from swarm_platform.controller.client import SwarmClient


COORDINATOR_IP = "10.15.2.63"  # change if needed


async def send(robot, message):
    reader, writer = await asyncio.open_connection(
        robot["ip"],
        robot["port"],
    )

    writer.write((json.dumps(message) + "\n").encode())
    await writer.drain()

    try:
        response = await reader.readline()
        if response:
            print(robot["robot_id"], response.decode().strip())
    except Exception as e:
        print(f"[ERROR] {robot['robot_id']}: {e}")

    writer.close()
    await writer.wait_closed()


async def broadcast(robots, message):
    await asyncio.gather(*(send(r, message) for r in robots))


async def main():
    client = SwarmClient(COORDINATOR_IP)

    robots = await client.list_robots()

    print("\n=== Robots ===")
    for r in robots:
        print(f"{r['robot_id']} -> {r['ip']}:{r['port']}")

    print("\n=== STARTING OBSTACLE AVOIDANCE ===")

    await broadcast(
        robots,
        {
            "type": "start_experiment",
            "name": "obstacle_avoidance",
            "config": {},
        },
    )

    print("\nCommands:")
    print("  p = pause")
    print("  r = resume")
    print("  s = stop")
    print("  q = quit\n")

    while True:
        cmd = input("> ").strip().lower()

        if cmd == "p":
            print("Pausing...")
            await broadcast(robots, {"type": "pause"})

        elif cmd == "r":
            print("Resuming...")
            await broadcast(robots, {"type": "resume"})

        elif cmd == "s":
            print("Stopping...")
            await broadcast(robots, {"type": "stop"})
            break

        elif cmd == "q":
            break


if __name__ == "__main__":
    asyncio.run(main())