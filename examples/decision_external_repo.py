"""Example script: install/run a "decision making" experiment from an external robot-code repo.

Connects to the coordinator, installs and activates the
`thymio_decision_making` project on a fixed set of hosts, starts the
`active_inference_noisy_quality_switch` experiment session (active
inference under elevated observation noise, with option 0/1 qualities
swapping 60s into the run), and lets the user interactively pause/resume/stop
it before collecting and deleting logs. The session is configured with a
fixed EXPERIMENT_DURATION_SECONDS (5 minutes) so it stops itself even if
nobody presses "s", keeping runs comparable. On exit (including via
exception), attempts to stop the session as a cleanup step.
"""

import asyncio
import time

from swarm_platform.config import COORDINATOR_IP
from swarm_platform.controller.client import SwarmClient
from swarm_platform.utils.unpack_results import (
    unpack_and_aggregate,
)

GITHUB_URL = "https://github.com/lmschw/thymio_decision_making"
SESSION_NAME = "weighted_voter_quality_switch-run"
EXPERIMENT_NAME = "weighted_voter_quality_switch"
HOSTS = ["thymio-01", 
        "thymio-03", 
        "thymio-04",
        "thymio-05",
        "thymio-06",
        "thymio-07",
        "thymio-08",
        "thymio-09",
        "thymio-10",
        "thymio-13",
        "thymio-15",
        "thymio-17",
        "thymio-18",
        "thymio-19",
        "thymio-20",
        "thymio-22",
        "thymio-23",
        "thymio-24",
        "thymio-25",
        ]
EXPERIMENT_DURATION_SECONDS = 5
EXPERIMENT_SWAP_SECONDS = 2

async def send_swap_command(session, start_time):
    target_time = start_time + EXPERIMENT_SWAP_SECONDS
    delay = target_time - time.monotonic()

    if delay > 0:
        await asyncio.sleep(delay)

    print(f"Sending swap command at {time.monotonic() - start_time:.3f}s")
    await session.send_internal_update("swap")

async def main() -> None:
    """Run the decision-making example end-to-end against the coordinator.

    Installs and activates the external project, starts an experiment
    session, then loops reading pause/resume/stop commands from stdin
    until either the user stops the session or EXPERIMENT_DURATION_SECONDS
    elapses, after which logs are collected and deleted. A `finally` block
    attempts to stop the session again as a safety net.
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

        print(f"Starting (duration={EXPERIMENT_DURATION_SECONDS}s)...")
        start_time = time.monotonic()
        await session.start(
            EXPERIMENT_NAME,
        )
        swap_task = asyncio.create_task(
            send_swap_command(session, start_time)
        )


        while True:

            try:
                cmd = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, input, "\n[p]ause  [r]esume  [s]top > "
                    ),
                    timeout=max(0, EXPERIMENT_DURATION_SECONDS - (time.monotonic() - start_time)),
                )
            except asyncio.TimeoutError:
                print("Experiment complete. Stopping...")
                await session.stop()
                break

            cmd = cmd.strip().lower()

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

        unpack_and_aggregate(f"results/{SESSION_NAME}", f"results/{SESSION_NAME}/processed")


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