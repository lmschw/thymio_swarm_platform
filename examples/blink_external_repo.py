import asyncio

from swarm_platform.controller.client import SwarmClient

async def main():

    client = SwarmClient("10.15.2.63")

    project = client.project(
        "https://github.com/lmschw/thymio_raspberry_swarm_control"
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