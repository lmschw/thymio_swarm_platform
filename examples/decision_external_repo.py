import asyncio

from swarm_platform.controller.client import SwarmClient
from swarm_platform.utils.utils import save_robot_info_to_csv

COORDINATOR_IP = "10.15.2.63"
GITHUB_URL = "https://github.com/lmschw/thymio_decision_making"
SESSION_NAME = "colour-recognition-run"
EXPERIMENT_NAME = "colour_recognition"
HOSTS = []

async def main():

    try:
        client = SwarmClient(COORDINATOR_IP)

        save_robot_info_to_csv(client)

        project = client.project(GITHUB_URL, HOSTS)

        print("Installing...")
        await project.install()

        print("Updating...")
        await project.update()

        print("Activating...")
        await project.activate()

        print("Activating session...")
        session = project.session(SESSION_NAME)

        print("Starting...")
        await session.start(EXPERIMENT_NAME)

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

        print("Stopping...")
        await session.stop()

        print("Collecting logs...")
        await session.collect_logs()

        print("Deleting logs...")
        await session.delete_logs()

        print("Done.")

    finally:
        print("\nStopping swarm...")
        try:
            await session.stop()
        except Exception as e:
            print(f"Failed to stop swarm: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass