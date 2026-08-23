"""Controller-side launcher for energy_efficient_flocking's unified position/heading/speed
calibration experiment -- run this BEFORE hebbian_swarm_trial.py (same directory).
SUPERSEDES both hebbian_pose_calibration.py and hebbian_speed_calibration.py: the PI-side
experiment (diagnostics/calibrate_position_heading_experiment.py) now derives
POSITION_AXES, HEADING_OFFSET_RAD, AND MOTOR_UNITS_PER_MPS from one straight-line drive,
instead of a manual eyeball-the-live-feed pass plus a separate speed sweep. See that
repo's ants26_replication/hardware_deployment/README.md "Calibration" section and
calibrate_position_heading_experiment.py's own docstring for what it measures and why
(no wheel odometry on this platform, so OptiTrack position deltas are the only ground
truth available).

MOTOR_TARGETS defaults to a SINGLE value, not a multi-point sweep: real Thymios don't
drive perfectly straight, and this platform can't drive a robot back to an exact start
position/heading between legs, so a multi-leg sweep lets one bad/curved leg physically
displace every leg after it (see calibrate_position_heading_experiment.py's docstring).
One ~10s drive is normally enough. If a run looks bad, manually put each robot back at
its start position and just re-run this launcher (still with one target) rather than
adding more targets to MOTOR_TARGETS.

KNOWN_UP_AXIS is passed through so the Pi-side experiment can skip up-axis auto-detection
entirely in favor of a value you already know for certain (see its definition below for
why this rig sets it rather than relying on auto-detection).

Deploys the `calibrate_position_heading` experiment (registered in that repo's own
swarm_project.yaml, same REPOSITORY as hebbian_swarm_trial.py) to all HOSTS at once,
waits for it to finish, collects logs, and prints:
  - a per-robot table (position axes, heading offset for each ROTATION_SIGN hypothesis,
    motor units per m/s)
  - POSITION_AXES/MOTOR_UNITS_PER_MPS recommendations aggregated across ALL robots (these
    are shared constants -- one controller_config.py is deployed to every Pi)
  - HEADING_OFFSET_RAD is reported per-robot AND aggregated, but flagged if robots
    disagree with each other by more than noise would explain -- unlike the other two,
    it's plausible for this to genuinely differ per robot if their rigid bodies weren't
    all defined with the same "front" convention in Motive, in which case you may need
    per-robot values instead of one shared constant.

ROTATION_SIGN still isn't calibrated by this test (a straight-line drive carries no
information about turn direction) -- observe it directly from hebbian_swarm_trial.py's
actual behavior (flip it if a deployed robot spins the wrong way), same as before.

Physical setup: give every robot in HOSTS a clear, straight runway (a couple of meters)
and make sure none of their runways cross -- they calibrate independently and don't sense
each other.
"""
import asyncio

from swarm_platform.config import COORDINATOR_IP
from swarm_platform.controller.client import SwarmClient
from swarm_platform.utils.unpack_results import unpack_and_aggregate

REPOSITORY = "https://github.com/lmschw/energy_efficient_flocking.git"
HOSTS = ["thymio-17", "thymio-18", "thymio-20"]
SESSION_NAME = "calibrate-position-heading-run"
EXPERIMENT_NAME = "calibrate_position_heading"

MOTOR_TARGETS = [300]  # single attempt by default -- see module docstring for why
HOLD_SECONDS = 10.0
SETTLE_SECONDS = 2.0

# This rig's Motive ground plane is confirmed Y-up (axis 1) by direct observation. Real
# calibration runs showed per-robot R^2-based up-axis auto-detection disagreeing with
# each other AND with this known-correct answer (all three picked axis 0 or 2 instead of
# 1), most likely because a robot's tracked marker pitches slightly under acceleration/
# deceleration -- a real, structured trend on the true up axis, not pure noise, which
# defeats a fit-quality heuristic same as it defeats a raw-slope one. Skip guessing
# entirely and tell the experiment what's already known. Set to None to fall back to
# auto-detection (e.g. if you move to a different, uncharacterized rig).
KNOWN_UP_AXIS = 1
# Wall-clock budget: len(targets) * (hold + settle) per robot, run in parallel across
# HOSTS, plus a fixed buffer for install/activate/start round-trip latency.
RUN_SECONDS = len(MOTOR_TARGETS) * (HOLD_SECONDS + SETTLE_SECONDS) + 15

# Legs disagreeing by more than this (radians) within one robot, or robots disagreeing
# with each other by more than this, gets flagged rather than silently averaged over.
HEADING_DISAGREEMENT_THRESHOLD_RAD = 0.15


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
        "motor_targets": MOTOR_TARGETS,
        "hold_seconds": HOLD_SECONDS,
        "settle_seconds": SETTLE_SECONDS,
        "known_up_axis": KNOWN_UP_AXIS,
    }
    host_configs = {h: {"self_hostname": h} for h in HOSTS}

    print(f"Starting calibration sweep on {HOSTS} (~{RUN_SECONDS:.0f}s)... "
          f"give every robot a clear, straight, obstacle-free runway.")
    await session.start(EXPERIMENT_NAME, config=shared_config, host_configs=host_configs)

    await asyncio.sleep(RUN_SECONDS)

    print("Stopping...")
    await session.stop()

    print("Collecting logs...")
    await session.collect_logs(output_dir="results")
    df = unpack_and_aggregate(f"results/{SESSION_NAME}", f"results/{SESSION_NAME}/processed")

    print("Deleting remote logs...")
    await session.delete_logs()

    summary = df[df["phase"] == "summary"].copy()
    if summary.empty:
        print("\nNo summary rows found -- check the per-robot output above/logs for "
              "tracking or runway issues before retrying.")
        return

    cols = ["hostname", "position_axes", "axes_agree",
            "heading_offset_if_rotation_sign_positive", "heading_offset_if_rotation_sign_negative",
            "recommended_units_per_mps", "n_legs_usable", "n_legs_total"]
    print("\n=== Per-robot results ===")
    print(summary[cols].to_string(index=False))

    # POSITION_AXES and MOTOR_UNITS_PER_MPS: shared constants, one recommendation across all robots.
    axes_counts = summary["position_axes"].value_counts()
    recommended_axes = axes_counts.idxmax()
    axes_agree_across_robots = len(axes_counts) == 1
    mean_units_per_mps = summary["recommended_units_per_mps"].mean()

    print("\n=== Aggregated recommendations (shared constants -- one controller_config.py "
          "for every Pi) ===")
    print(f"POSITION_AXES = {recommended_axes}" +
          ("" if axes_agree_across_robots else
           f"  -- WARNING: robots disagreed ({dict(axes_counts)}), do not trust a single "
           f"shared value until you understand why"))
    print(f"MOTOR_UNITS_PER_MPS = {mean_units_per_mps:.2f}")

    # HEADING_OFFSET_RAD: PER-ROBOT, not aggregated to one shared constant -- real robots
    # have disagreed by more than measurement noise would explain (their rigid bodies
    # most likely weren't defined with the same "front" convention in Motive), so
    # controller_config.py's HEADING_OFFSET_RAD is a dict keyed by hostname. Print a
    # ready-to-paste dict literal for each ROTATION_SIGN hypothesis -- pick whichever
    # one matches your separately-observed ROTATION_SIGN.
    print("\n=== HEADING_OFFSET_RAD (per robot -- paste directly into controller_config.py) ===")
    print("ROTATION_SIGN is NOT determined by this test -- pick whichever dict below matches "
          "your separately-observed ROTATION_SIGN.")
    print("\nif ROTATION_SIGN = 1.0:")
    print("HEADING_OFFSET_RAD = {")
    for _, row in summary.iterrows():
        print(f'    "{row["hostname"]}": {row["heading_offset_if_rotation_sign_positive"]:+.4f},')
    print("}")
    print("\nif ROTATION_SIGN = -1.0:")
    print("HEADING_OFFSET_RAD = {")
    for _, row in summary.iterrows():
        print(f'    "{row["hostname"]}": {row["heading_offset_if_rotation_sign_negative"]:+.4f},')
    print("}")

    pos_vals = summary["heading_offset_if_rotation_sign_positive"].to_numpy()
    pos_spread = float(pos_vals.max() - pos_vals.min()) if len(pos_vals) > 1 else 0.0
    if pos_spread > HEADING_DISAGREEMENT_THRESHOLD_RAD:
        print(f"\nNote: robots disagree by up to {pos_spread:.4f} rad (> this script's "
              f"{HEADING_DISAGREEMENT_THRESHOLD_RAD} rad noise threshold) -- expected, and "
              f"exactly why this is per-robot rather than one shared value. Just make sure "
              f"every robot you're deploying actually has its own entry above (or falls back "
              f"to HEADING_OFFSET_RAD_DEFAULT with a one-time warning, printed by pose_utils.py "
              f"on the Pi -- see controller_config.py).")

    print("\nUpdate POSITION_AXES, HEADING_OFFSET_RAD, and MOTOR_UNITS_PER_MPS in "
          "energy_efficient_flocking's ants26_replication/hardware_deployment/"
          "controller_config.py, commit+push, then determine ROTATION_SIGN by observing a "
          "turn before running hebbian_swarm_trial.py.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
