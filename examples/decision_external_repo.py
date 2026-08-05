"""Example script: install/run a "decision making" experiment from an external robot-code repo.

Connects to the coordinator, installs and activates the
`thymio_decision_making` project on a fixed set of hosts, starts the
`communication_test` experiment session, and lets the user interactively
pause/resume/stop it before collecting and deleting logs. On exit (including
via exception), attempts to stop the session as a cleanup step.
"""

import asyncio

from swarm_platform.config import COORDINATOR_IP
from swarm_platform.controller.client import SwarmClient

GITHUB_URL = "https://github.com/lmschw/thymio_decision_making"
SESSION_NAME = "communication_test-run"
EXPERIMENT_NAME = "communication_test"
HOSTS = ["thymio-01", "thymio-04"]


async def main() -> None:
    """Run the decision-making example end-to-end against the coordinator.

    Installs and activates the external project, starts an experiment
    session, then loops reading pause/resume/stop commands from stdin until
    the user stops the session, after which logs are collected and deleted.
    A `finally` block attempts to stop the session again as a safety net.
    """

    try:
        client = SwarmClient(COORDINATOR_IP)

        #await save_robot_info_to_csv(client)

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

            cmd = (await asyncio.get_event_loop().run_in_executor(
                None, input, "\n[p]ause  [r]esume  [s]top > "
            )).strip().lower()

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