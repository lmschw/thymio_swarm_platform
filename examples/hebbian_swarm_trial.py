"""Controller-side launcher for the 3-agent Hebbian ABCD hardware trial from
energy_efficient_flocking. Same pattern as decision_external_repo.py in this directory --
REPOSITORY is a self-contained project (has its own swarm_project.yaml at
ants26_replication/hardware_deployment/ inside that repo; the rest of that repo, e.g. its
training code, is discarded by ProjectManager when deploying to each Pi).

The controller logic (sensing, the Hebbian MLP, motor conversion, calibration constants)
lives entirely in that repo -- this script only drives the platform's install/start/stop
lifecycle and pulls back logs. See
energy_efficient_flocking/ants26_replication/hardware_deployment/README.md for the full
walkthrough, calibration steps, and disclosed sim-to-real caveats before trusting a real
run.

Prerequisites -- do NOT run this until all of these are true:
1. `python local_test_harness.py` (in that repo's hardware_deployment/) passes locally.
2. Calibrated on your actual rig: diagnostics/print_poses_experiment.py (POSITION_AXES,
   HEADING_OFFSET_RAD) and hebbian_speed_calibration.py (this directory, for
   MOTOR_UNITS_PER_MPS) -- controller_config.py's hardware-calibration constants in that
   repo are no longer placeholders.
3. Those calibration edits are committed and pushed to REPOSITORY's remote -- the Pis
   pull via git, they never see your local checkout of energy_efficient_flocking.

Genome: hebbian_save_battery_avoid_all_best.npy -- trained through all 3 curriculum
stages (walk_left -> save_battery_avoid_wall -> save_battery_avoid_all) at the paper's
default n_agents=20, NOT re-trained at n_agents=3. Running it with only 2 real neighbors
is a real, disclosed sim-to-real gap -- see that repo's README.md.
"""
import asyncio
import time

from swarm_platform.config import COORDINATOR_IP
from swarm_platform.controller.client import SwarmClient
from swarm_platform.utils.unpack_results import unpack_and_aggregate

REPOSITORY = "https://github.com/lmschw/energy_efficient_flocking.git"
HOSTS = ["thymio-17", "thymio-18", "thymio-20"]
SESSION_NAME = "hebbian-swarm-3agent-run"
EXPERIMENT_NAME = "hebbian_swarm"
GENOME_PATH_ON_PI = "hebbian_save_battery_avoid_all_best.npy"
EXPERIMENT_DURATION_SECONDS = 120  # first live trial: keep this short, extend once you've
                                    # watched it behave sanely for a couple of minutes.


async def main():
    client = SwarmClient(COORDINATOR_IP)
    project = client.project(REPOSITORY, HOSTS)

    print("Installing...")
    await project.install()
    print("Updating...")
    await project.update()
    print("Activating...")
    await project.activate()

    session = project.session(SESSION_NAME)

    shared_config = {
        "genome_path": GENOME_PATH_ON_PI,
        "hostnames": HOSTS,  # identical list/order on every robot
    }
    host_configs = {h: {"self_hostname": h} for h in HOSTS}  # differs per robot

    print(f"Starting (duration={EXPERIMENT_DURATION_SECONDS}s)...")
    start_time = time.monotonic()
    await session.start(EXPERIMENT_NAME, config=shared_config, host_configs=host_configs)

    try:
        while True:
            remaining = EXPERIMENT_DURATION_SECONDS - (time.monotonic() - start_time)
            try:
                cmd = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, input, "\n[p]ause  [r]esume  [s]top > "
                    ),
                    timeout=max(0, remaining),
                )
            except asyncio.TimeoutError:
                print("Experiment duration elapsed. Stopping...")
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
                break
    finally:
        print("Stopping...")
        try:
            await session.stop()
        except Exception as e:
            print(f"Failed to stop swarm: {e}")

        print("Collecting logs...")
        await session.collect_logs(output_dir="results")
        unpack_and_aggregate(f"results/{SESSION_NAME}", f"results/{SESSION_NAME}/processed")

        print("Deleting remote logs...")
        await session.delete_logs()
        print("Done.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
