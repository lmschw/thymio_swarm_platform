"""Controller-side launcher for energy_efficient_flocking's diagnostics/print_poses_experiment.py
-- run this FIRST, before hebbian_speed_calibration.py and hebbian_swarm_trial.py (same
directory). Calibrates POSITION_AXES, HEADING_OFFSET_RAD, and (indirectly, by watching
turn direction later) ROTATION_SIGN in that repo's controller_config.py. See that repo's
ants26_replication/hardware_deployment/README.md "Calibration" section.

Unlike the other two launchers, this one doesn't collect/print anything itself --
print_poses_experiment.py prints on the PI, not back to this script, so you read the
values live over SSH instead (see below). This script just starts/stops the session and
gets out of the way.

How to actually calibrate, once this is running:
1. SSH into ONE Pi at a time (e.g. `ssh thymio-15`) and run:
       journalctl -u swarm-daemon.service -f
   to watch that robot's own printed pose lines live (swarm-daemon.service is how the
   platform runs the daemon on every Pi -- see setup_scripts/swarm_platform_setup.sh).
2. Physically move/rotate that robot and watch `raw position=...` change -- figure out
   which of OptiTrack's (x, y, z) components change the way you'd expect as you move the
   robot along the ground plane; that pair is POSITION_AXES.
3. Point the robot in whichever physical direction you want this codebase's heading=0 to
   mean (recall: the trained controller always migrates toward -x in its own frame, i.e.
   away from heading=0), and read off `raw_yaw=...`; set HEADING_OFFSET_RAD to minus that
   value.
4. Repeat for the other two robots -- POSITION_AXES/HEADING_OFFSET_RAD must be correct
   for ALL of them (a single shared controller_config.py is deployed to every Pi).
5. Edit controller_config.py, commit + push, then re-run this script to verify (the
   printed `-> sim frame x=... y=... heading=...` line uses your new values).
6. Stop this script (type 's') when done. ROTATION_SIGN isn't calibrated here -- it's
   easiest to observe directly from hebbian_swarm_trial.py's actual behavior (flip it if
   a deployed robot spins the wrong way).
"""
import asyncio

from swarm_platform.config import COORDINATOR_IP
from swarm_platform.controller.client import SwarmClient

REPOSITORY = "https://github.com/lmschw/energy_efficient_flocking.git"
HOSTS = ["thymio-15", "thymio-16", "thymio-17"]
SESSION_NAME = "print-poses-calibration"
EXPERIMENT_NAME = "print_poses"


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

    shared_config = {"hostnames": HOSTS}
    host_configs = {h: {"self_hostname": h} for h in HOSTS}

    print(f"Starting on {HOSTS}. SSH into a Pi and run "
          f"`journalctl -u swarm-daemon.service -f` to watch its printed poses live.")
    await session.start(EXPERIMENT_NAME, config=shared_config, host_configs=host_configs)

    try:
        while True:
            cmd = await asyncio.get_event_loop().run_in_executor(
                None, input, "\n[p]ause  [r]esume  [s]top > "
            )
            cmd = cmd.strip().lower()
            if cmd == "p":
                await session.pause()
            elif cmd == "r":
                await session.resume()
            elif cmd == "s":
                break
    finally:
        print("Stopping...")
        try:
            await session.stop()
        except Exception as e:
            print(f"Failed to stop swarm: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
