"""Controller-side launcher for energy_efficient_flocking's diagnostics/print_poses_experiment.py
-- run this FIRST, before hebbian_speed_calibration.py and hebbian_swarm_trial.py (same
directory). Calibrates POSITION_AXES, HEADING_OFFSET_RAD, and (indirectly, by watching
turn direction later) ROTATION_SIGN in that repo's controller_config.py -- and, once those
are set, this is also how you measure CORRIDOR_Y_MIN/MAX for the wall-safety governor. See
that repo's ants26_replication/hardware_deployment/README.md "Calibration" section.

ONE ROBOT AT A TIME: pass its hostname as the only argument, e.g.
    python3 hebbian_pose_calibration.py thymio-17
Point-and-sample, not continuous tracking: place the robot, physically step clear of the
tracked volume (so your own body isn't occluding its markers -- bending over the robot to
move it can block line-of-sight to some cameras and not others, which looks exactly like a
frozen/broken reading even though nothing is actually wrong), then press 'p' or 'r' in THIS
script's terminal to take one reading.

Unlike watching journalctl live (messy, hard to pull a clean number back out of), this
script now collects each sample's logged data itself and prints a clean table when you stop
it (type 's') -- no SSH/journalctl needed at all for normal use. If you want to watch samples
appear live as a secondary check, `ssh <hostname>` and `journalctl -u swarm-daemon.service -f`
still works (each sample still prints one line there too), but it's optional now.

How to actually calibrate:
1. Run this script with the hostname you want to calibrate right now.
2. Physically place/point the robot where or however you want to measure it, then STEP
   AWAY from the tracked volume so your own body isn't occluding it.
3. Press 'p' (or 'r' -- both do the same thing, see print_poses_experiment.py's docstring
   for why). This takes exactly one fresh reading.
4. For POSITION_AXES: sample at two different, known positions along the ground plane and
   see which of the raw (x, y, z) components changed the way you'd expect in the final
   table; that pair is POSITION_AXES. For HEADING_OFFSET_RAD: point the robot in whichever
   physical direction you want this codebase's heading=0 to mean (recall: the trained
   controller always migrates toward -x in its own frame, i.e. away from heading=0),
   sample, and read off raw_yaw in the table; set HEADING_OFFSET_RAD to minus that value.
   For CORRIDOR_Y_MIN/MAX: sample at each wall; use the smaller/larger of the two sampled
   sim_y values (with a little headroom inward).
5. Type 's' to stop -- prints a table of every sample taken this run, in order.
6. Repeat for each of the other robots (one at a time) -- POSITION_AXES/HEADING_OFFSET_RAD
   must be correct for ALL of them (a single shared controller_config.py is deployed to
   every Pi); CORRIDOR_Y_MIN/MAX is shared across all robots too (one corridor).
7. Edit controller_config.py, commit + push, then re-run this script to verify.
8. ROTATION_SIGN isn't calibrated here -- it's easiest to observe directly from
   hebbian_swarm_trial.py's actual behavior (flip it if a deployed robot spins the wrong way).
"""
import asyncio
import sys

import pandas as pd

from swarm_platform.config import COORDINATOR_IP
from swarm_platform.controller.client import SwarmClient
from swarm_platform.utils.unpack_results import unpack_and_aggregate

REPOSITORY = "https://github.com/lmschw/energy_efficient_flocking.git"
SESSION_NAME = "print-poses-calibration"
EXPERIMENT_NAME = "print_poses"


async def main():
    if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} <hostname>   e.g. thymio-17")
        return
    hostname = sys.argv[1]
    hosts = [hostname]

    client = SwarmClient(COORDINATOR_IP)
    project = client.project(REPOSITORY, hosts)

    print("Installing...")
    await project.install()
    print("Updating...")
    await project.update()
    print("Activating...")
    await project.activate()

    session = project.session(SESSION_NAME)

    shared_config = {"hostnames": hosts}
    host_configs = {hostname: {"self_hostname": hostname}}

    print(f"Starting on {hostname}. Place/point the robot, step clear of the tracked "
          f"volume, then press 'p' or 'r' below to take a reading.")
    await session.start(EXPERIMENT_NAME, config=shared_config, host_configs=host_configs)

    try:
        while True:
            cmd = await asyncio.get_event_loop().run_in_executor(
                None, input, "\n[p]/[r] sample point now  [s]top > "
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

        print("Collecting samples...")
        await session.collect_logs(output_dir="results")
        df = unpack_and_aggregate(f"results/{SESSION_NAME}", f"results/{SESSION_NAME}/processed")

        print("Deleting remote logs...")
        await session.delete_logs()

        if df.empty or "sample" not in df.columns:
            print("\nNo samples recorded -- did you press 'p'/'r' at least once before 's'?")
            return

        df = df.sort_values("sample")
        cols = ["sample", "trigger", "position", "raw_yaw", "sim_x", "sim_y", "sim_heading"]
        print(f"\n=== {hostname}: {len(df)} sample(s), in order ===")
        with pd.option_context("display.max_colwidth", None, "display.width", None):
            print(df[cols].to_string(index=False))

        if len(df) >= 2:
            y_vals = df["sim_y"].dropna()
            if len(y_vals) >= 2:
                print(f"\nIf these were your two corridor-wall samples: "
                      f"CORRIDOR_Y_MIN={y_vals.min():.3f}  CORRIDOR_Y_MAX={y_vals.max():.3f} "
                      f"(add a little headroom inward before using these).")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
