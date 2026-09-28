"""Controller-side launcher for the LJ baseline (paper Table 3 "standard collective
motion baseline", the cluster-4 comparison point in Fig. 5a) hardware trial from
energy_efficient_flocking. Sibling to hebbian_swarm_trial.py in this directory -- same
platform install/start/stop lifecycle, same REPOSITORY (this launcher only points
client.project() at the "lj_baseline" experiment registered in that repo's
swarm_project.yaml instead of "hebbian_swarm"). No genome_path: the LJ controller is a
fixed control law, not a trained/plastic one -- see
energy_efficient_flocking/ants26_replication/hardware_deployment/lj_baseline_experiment.py.

Prerequisites -- do NOT run this until:
1. `python local_test_harness.py` (in that repo's hardware_deployment/) passes locally,
   including the "Testing LJBaselineExperiment" section.
2. Your rig is ALREADY calibrated for hebbian_swarm_trial.py (POSITION_AXES,
   HEADING_OFFSET_RAD, ROTATION_SIGN, MOTOR_UNITS_PER_MPS, CORRIDOR_Y_MIN/MAX in that
   repo's controller_config.py) -- this is the same physical rig/robots/OptiTrack setup,
   nothing about the LJ baseline needs its own recalibration. If you've already run
   hebbian_swarm_trial.py successfully, skip straight to running this.
"""
import asyncio
import time

from swarm_platform.config import COORDINATOR_IP
from swarm_platform.controller.client import SwarmClient
from swarm_platform.utils.unpack_results import unpack_and_aggregate

REPOSITORY = "https://github.com/lmschw/energy_efficient_flocking.git"
# HOSTS = ["thymio-01", "thymio-07", "thymio-08", "thymio-09", "thymio-11",
#          "thymio-25", "thymio-19", "thymio-17",  "thymio-15", "thymio-03",
#          "thymio-12", "thymio-18", "thymio-14", "thymio-20", "thymio-04"]
HOSTS = ["thymio-01", "thymio-07", "thymio-08", "thymio-09", "thymio-11",
         "thymio-25", "thymio-19", "thymio-17",  "thymio-15", "thymio-03"]
SESSION_NAME = f"lj-baseline-10agent-run-{int(time.time())}"
EXPERIMENT_NAME = "lj_baseline"
EXPERIMENT_DURATION_SECONDS = 120  # match the Hebbian trials' duration for a fair comparison;
                                    # shorten for a first sanity check if you want.


async def main():
    client = SwarmClient(COORDINATOR_IP)
    project = client.project(REPOSITORY, HOSTS)

    # print("Installing...")
    # await project.install()
    # print("Updating...")
    # await project.update()
    print("Activating...")
    await project.activate()

    session = project.session(SESSION_NAME)

    shared_config = {
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
