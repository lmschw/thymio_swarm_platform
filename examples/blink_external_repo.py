"""Example script: install/run a "blink" experiment from an external robot-code repo.

Connects to the coordinator, installs and activates the
`thymio_raspberry_swarm_control` project on a set of hosts, starts the
`optitrack_positions` experiment session, and lets the user interactively
pause/resume/stop it before collecting logs.
"""

import asyncio

from swarm_platform.config import COORDINATOR_IP
from swarm_platform.controller.client import SwarmClient
from swarm_platform.utils.unpack_results import (
    unpack_and_aggregate,
)

async def main() -> None:
    """Run the blink example end-to-end against the coordinator.

    Installs and activates the external project, starts an experiment
    session, then loops reading pause/resume/stop commands from stdin until
    the user stops the session, after which logs are collected.
    """

    client = SwarmClient(COORDINATOR_IP)

    repository_link = "https://github.com/lmschw/thymio_raspberry_swarm_control"
    experiment_name = "optitrack_positions"
    session_name = "optitrack_positions-run"
    hosts = []

    #await save_robot_info_to_csv(client)

    project = client.project(
        repository=repository_link,
        hosts=hosts,
    )

    #print("Installing...")
    await project.install()

    #print("Updating...")
    await project.update()

    #print("Activating...")
    await project.activate()

    #print("Activating session...")
    session = project.session(session_name)

    #print("Starting...")
    await session.start(experiment_name)

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

    #print("Stopping...")
    await session.stop()

    # print("Collecting logs...")
    await session.collect_logs()

    unpack_and_aggregate(f"results/{session_name}", f"results/{session_name}/processed")

    # print("Deleting logs...")
    await session.delete_logs()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())