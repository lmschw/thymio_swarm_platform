import asyncio

from swarm_platform.controller.client import SwarmClient
from swarm_platform.utils.utils import save_robot_info_to_csv

async def main():

    client = SwarmClient("10.15.2.63")
    hosts = ["thymio-04"]

    save_robot_info_to_csv(client)

    project = client.project(
        repository="https://github.com/lmschw/thymio_raspberry_swarm_control",
        hosts=hosts,
    )

    #print("Installing...")
    await project.install()

    #print("Updating...")
    await project.update()

    #print("Activating...")
    await project.activate()

    #print("Activating session...")
    session = project.session("test-run")

    #print("Starting...")
    await session.start("blink")

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

    #print("Stopping...")
    await session.stop()

    # print("Collecting logs...")
    # await session.collect_logs()

    # print("Deleting logs...")
    # await session.delete_logs()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())