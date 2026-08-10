"""Example script: install/run a "decision making" experiment from an external robot-code repo.

Connects to the coordinator, installs and activates the
`thymio_decision_making` project on a fixed set of hosts, starts the
`active_inference_noisy_quality_switch` experiment session (active
inference under elevated observation noise, with option 0/1 qualities
swapping at tick 1200), and lets the user interactively pause/resume/stop
it before collecting and deleting logs. The session is configured with a
fixed EXPERIMENT_DURATION_SECONDS (5 minutes) so it stops itself even if
nobody presses "s", keeping runs comparable. On exit (including via
exception), attempts to stop the session as a cleanup step.
"""

import asyncio
import time

from swarm_platform.config import COORDINATOR_IP
from swarm_platform.controller.client import SwarmClient

GITHUB_URL = "https://github.com/lmschw/thymio_decision_making"
SESSION_NAME = "active-inference-noisy-quality-switch-run"
EXPERIMENT_NAME = "active_inference_noisy_quality_switch"
HOSTS = ["thymio-01", "thymio-04"]
EXPERIMENT_DURATION_SECONDS = 5 * 60


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
        await session.start(
            EXPERIMENT_NAME,
            config={"duration_seconds": EXPERIMENT_DURATION_SECONDS},
        )

        # Each robot stops itself once duration_seconds elapses (see
        # `duration_seconds` on the experiment classes), but this script
        # would otherwise sit forever at the input() prompt waiting for a
        # manual "s" - race the prompt against the same deadline so it
        # moves on to collect/delete logs on its own once time is up.
        start_time = time.monotonic()

        while True:

            remaining = EXPERIMENT_DURATION_SECONDS - (time.monotonic() - start_time)
            if remaining <= 0:
                print(f"\n{EXPERIMENT_DURATION_SECONDS}s elapsed - stopping automatically.")
                break

            try:
                cmd = (await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, input, "\n[p]ause  [r]esume  [s]top > "
                    ),
                    timeout=remaining,
                )).strip().lower()
            except asyncio.TimeoutError:
                print(f"\n{EXPERIMENT_DURATION_SECONDS}s elapsed - stopping automatically.")
                break

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