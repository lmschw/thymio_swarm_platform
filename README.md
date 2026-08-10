# Thymio Swarm Platform

This repository allows you to run a swarm of Thymio II Wireless robots, each with a Raspberry Pi attached, from a single controlling computer. It takes care of robot discovery, experiment lifecycle (start/pause/resume/stop), log collection and optional motion-capture (OptiTrack) tracking, so that project code can focus on the actual swarm behaviour instead of networking and orchestration.

## Features

- Execute swarm experiments on 1 to n Raspberry Pi + Thymio II Wireless sets, from a single controller machine.
- Automatic robot discovery: Pis register themselves with a coordinator and send heartbeats, so the controller always knows which robots are currently online and how to reach them.
- Project-based experiments: experiment code lives in its own git repository (independent of this platform) and is installed/updated on the controller and every Pi with a couple of method calls. Multiple experiments can live in the same project and are selected by name at run time.
- Full session lifecycle: start, pause, resume and stop an experiment across the whole swarm (or a subset of hosts) with a single call, each broadcast concurrently to all targeted robots.
- A high-level `Robot` abstraction so experiment code doesn't need to deal with Aseba or `tdmclient` directly: motors, top LED, ground/proximity/accelerometer/button/temperature sensors, and inter-robot communication over the Thymio's proximity sensors (`send`/`receive`).
- Optional Pi camera support: robots with a camera attached can capture still images (`robot.camera_capture()`) for use in experiments; robots without one just run without it — no configuration needed.
- Per-robot CSV logging of state/commands during a run, collected from every agent after the experiment and collated into a single aggregated CSV file for analysis.
- Remote code updates: pushing an update to a project (or to the platform itself) pulls the latest code onto every Pi and restarts the daemon automatically.
- Optional OptiTrack integration: robots receive their live global pose (position + orientation) from a motion-capture system during an experiment.
- Small analysis/plotting utilities for aggregating logs, reconstructing trajectories and summarising results.

## Architecture

The architecture of this platform assumes the following setup:

- **Controller** – a computer that manages the experiments, i.e. sets up the config, sends commands to start, pause, stop etc. The code for this is in [swarm_platform/controller](swarm_platform/controller). This is typically your laptop/desktop.
- **Coordinator** – a Raspberry Pi (or any always-on machine on the network) that collects the IP addresses of the Pis on the Thymios and makes them available to the controller. The code for this is in [swarm_platform/coordinator](swarm_platform/coordinator). It should always remain on so that its IP address remains constant and stable for the whole network.
- **Robots** – 1 to n Raspberry Pis, each mounted on and connected by cable to a Thymio II Wireless. Each Pi runs a **daemon** ([swarm_platform/daemon](swarm_platform/daemon)) that talks to the Thymio (via the Thymio Device Manager and `tdmclient`) and to the controller/coordinator.

All of the components need to be on the same network. When a Pi is turned on, its daemon registers itself with the coordinator and periodically sends heartbeats. The coordinator drops any robot it hasn't heard from in 30 seconds. When you send a command to your swarm, the controller first retrieves the current list of active robots from the coordinator (hostname, IP, port), then talks to each robot's daemon directly.

```
 ┌────────────┐      list robots       ┌──────────────┐
 │ Controller │ ──────────────────────▶│  Coordinator │
 │ (your PC)  │◀────────────────────── │ (always-on)  │
 └────────────┘   robots{hostname:     └──────────────┘
       │             ip, port}                 ▲
       │  start/pause/resume/stop/...           │ register + heartbeat
       │  (direct TCP, one connection per robot)│
       ▼                                        │
 ┌────────────────────────────┐                 │
 │ Daemon on Raspberry Pi      │─────────────────┘
 │ (swarm_platform.daemon)     │
 │  - manages active project   │
 │  - runs experiment          │
 │  - logs to CSV              │
 └────────────┬───────────────┘
              │ tdmclient / Thymio Device Manager
              ▼
      ┌───────────────┐
      │ Thymio II      │
      │ Wireless robot │
      └───────────────┘
```

All communication uses newline-delimited JSON over plain TCP sockets:

- Coordinator listens on port **9100** (`register`, `heartbeat`, `list`).
- Each Pi's daemon listens on port **9000** (experiment control, project management, log streaming, etc. — see [swarm_platform/protocol](swarm_platform/protocol)).
- The Thymio Device Manager (TDM) listens locally on the Pi on port **8596**; the daemon talks to it through `tdmclient`.

Project code (the actual swarm behaviour/experiments) is contained in a **separate** git repository — only the run configuration/scripts live in this repository. That project repository is cloned both to the controller machine (into `projects/<repo-name>`, see [Project](swarm_platform/controller/project.py)) and to every Pi (into `active_project/`, see [ProjectManager](swarm_platform/projects/manager.py)). Different experiments can be defined in the same project repository and selected by name when starting a session (see [Examples](#examples) below).

Whenever the project or the platform code on a Pi is updated (`update_project` / `update_code`), the daemon process restarts itself so the newest version is running.

## Requirements

**Controller machine** (the computer you run experiments from):
- Python ≥ 3.11
- [`uv`](https://docs.astral.sh/uv/) (used to manage the virtual environment and run scripts)
- `git`
- Network access to the coordinator and to every robot's Pi

**Coordinator** (can be one of the Pis, or any always-on Linux machine on the same network):
- Python ≥ 3.11 and `uv`
- A stable IP address on the swarm's network

**Each robot's Raspberry Pi**:
- Raspberry Pi OS (or similar Linux) with `flatpak`, `git`, `python3-venv`
- The Mobsya Thymio Suite (`org.mobsya.ThymioSuite`), providing the Thymio Device Manager
- A Thymio II Wireless connected to the Pi via USB cable
- Python ≥ 3.11 and `uv`

**Optional — motion capture**:
- An OptiTrack/Motive setup streaming over NatNet, reachable from the controller machine (tracking data is broadcast to the robots by the controller, not read directly by the Pis)

**Optional — camera**:
- A Raspberry Pi camera module on any robot that needs one, plus `picamera2` (installed via `apt`, see [Camera (optional)](#camera-optional)) — no camera hardware or dependency is required on robots that don't use one.

Python dependencies (`tdmclient`, `numpy`, `pyyaml`, `pandas`, `natnet`, `matplotlib`, …) are declared in [pyproject.toml](pyproject.toml) and installed automatically by `uv sync`.

## Getting started

### 1. Set up the coordinator

Pick one always-on machine on the swarm network (this can be one of the robot Pis). Clone this repository onto it and install the coordinator as a systemd service:

```bash
git clone https://github.com/lmschw/thymio_swarm_platform
cd thymio_swarm_platform
./setup_scripts/install_coordinator_service.sh
```

This installs and starts a `swarm-coordinator` systemd service listening on port 9100. Note down this machine's IP address — it is needed by every Pi and by the controller.

### 2. Set up each robot's Raspberry Pi

On every Pi that has a Thymio II Wireless attached:

```bash
git clone https://github.com/lmschw/thymio_swarm_platform
cd thymio_swarm_platform

./setup_scripts/raspberry_pi_initial_setup.sh   # installs the Thymio Device Manager, USB rules, uv, etc. Reboot when it tells you to.
./setup_scripts/swarm_platform_setup.sh         # installs dependencies and the swarm-daemon systemd service
./setup_scripts/verify_installation.sh          # sanity-checks the whole setup
```

`swarm_platform_setup.sh` writes the coordinator's address to `/etc/swarm-platform.conf` (as `SWARM_COORDINATOR`/`SWARM_COORDINATOR_PORT`) — edit that file if your coordinator isn't at the default IP baked into the script, then restart the service with `sudo systemctl restart swarm-daemon`.

Each Pi's hostname is used as its robot id throughout the platform, so give each one a distinct, meaningful hostname (e.g. `thymio-01`, `thymio-02`, …) before running the setup.

#### Camera (optional)

If a Pi has a camera module attached, run the following once on that Pi (in addition to the steps above) to install `picamera2` and give the project's virtual environment access to it:

```bash
./setup_scripts/add_camera_support.sh
```

This is also folded into `raspberry_pi_initial_setup.sh`/`swarm_platform_setup.sh`, so it's unnecessary on a freshly-provisioned Pi — it exists for retrofitting a Pi that's already set up, without repeating the rest of the install. The daemon auto-detects the camera at startup: `robot.has_camera` reflects whether one was found, and `await robot.camera_capture(path=...)` (see below) works regardless of whether the machine you're reading this on has a camera attached.

Run `./setup_scripts/verify_camera.sh` afterwards to confirm the camera is detected, importable, capturable, and (if the daemon is running) actually reported by it — it leaves a test JPEG at `/tmp/camera_test_capture.jpg` for a manual visual check.

### 3. Set up the controller

On the machine you'll run experiments from:

```bash
git clone https://github.com/lmschw/thymio_swarm_platform
cd thymio_swarm_platform
uv sync
```

### 4. Create a project

Experiment code lives in its own repository, separate from this platform, containing a `swarm_project.yaml` manifest at its root:

```yaml
name: my-project
version: "0.1"

experiments:
  blink:
    class: my_project.experiments.blink.Blink
    tracking: false
  optitrack_positions:
    class: my_project.experiments.tracking_demo.TrackingDemo
    tracking: true

tracking:
  host: "10.0.10.4"           # NatNet server (Motive) address
  hostname_map:
    thymio-01: "Robot 1"      # maps Pi hostname -> Motive rigid body name
    thymio-02: "Robot 2"
  verbose: false
```

Each entry under `experiments` points to a class (`module.ClassName`, importable from the project root) that will be instantiated on the robot as `experiment_cls(robot=robot, config=config, logger=logger)`. The daemon expects it to expose:

- `async def run(self)` — the main control loop; runs until the experiment stops or is cancelled.
- `async def pause(self)` / `async def resume(self)` / `async def stop(self)` — lifecycle hooks called on the corresponding session commands.

`robot` is a [`Robot`](swarm_platform/robot/robot.py) instance giving access to `drive()`, `stop()`, `top_led()`, the various sensor readers, `send()`/`receive()` for inter-robot communication, `get_global_pose()`/`get_all_global_poses()` if tracking is enabled, and — on robots with a camera attached — `has_camera` / `await camera_capture(path=...)` to grab a still image. `logger` is a `SessionLogger` (see [Logging](#logging)) that the experiment can call `.log(state, command)` on every tick to persist a CSV row.

### 5. Write a controller script

```python
import asyncio
from swarm_platform.controller.client import SwarmClient

async def main():
    client = SwarmClient("10.15.2.63")  # coordinator IP

    project = client.project(
        repository="https://github.com/<you>/my-project",
        hosts=[],  # empty = all currently registered robots
    )

    await project.install()   # clone + activate on every host and locally
    # await project.update()  # pull latest changes instead, if already installed

    session = project.session("blink-run-1")  # session/log directory name

    await session.start("blink", config={"colour": [32, 0, 0]})

    await asyncio.sleep(30)

    await session.stop()
    await session.collect_logs()  # -> results/blink-run-1/<hostname>.csv

asyncio.run(main())
```

Run it with `uv run python your_script.py`. See [Examples](#examples) for two complete, more elaborate scripts.

### Using the OptiTrack functionality

If an experiment's config sets `tracking: true` (see the `swarm_project.yaml` snippet above), starting that experiment's session automatically:

1. Connects the controller to the NatNet server described in the project's top-level `tracking` block (`host`, `hostname_map`, `verbose`) via [`OptitrackClient`](swarm_platform/tracking/optitrack_client.py).
2. Starts a background loop on the controller that polls poses every 0.5s and broadcasts a `tracking_update` message with every mapped robot's position/orientation to all robots.
3. Each daemon stores the received poses, made available to the experiment through `robot.get_global_pose()` (this robot's own pose) and `robot.get_all_global_poses()` (every tracked robot's pose).

`hostname_map` maps each robot's Pi hostname to the name of the corresponding rigid body as defined in Motive — make sure every robot you want tracked has a rigid body defined and named accordingly. Tracking is stopped automatically when the session is stopped.

You can sanity-check your OptiTrack connection independently with `uv run python tasks/test_optitrack.py` (edit the `server_ip` at the top of the script first).

## Examples

The [examples](examples) directory contains two full end-to-end scripts that install a project, run one of its experiments interactively, and collect logs:

- [`blink_external_repo.py`](examples/blink_external_repo.py) — installs the `thymio_raspberry_swarm_control` project on all currently registered robots and runs its `optitrack_positions` experiment (tracking-enabled).
- [`decision_external_repo.py`](examples/decision_external_repo.py) — installs the `thymio_decision_making` project on a fixed pair of hosts (`thymio-01`, `thymio-04`) and runs its `communication_test` experiment, with a `finally` block that stops the session even on error/`Ctrl-C`.

Both follow the same pattern: `client.project(...)` → `project.install()`/`update()` → `project.session(...)` → `session.start(...)` → interactive `p`/`r`/`s` (pause/resume/stop) loop → `session.collect_logs()`.

The [tasks](tasks) directory contains small standalone scripts useful for day-to-day swarm management (all run with `uv run python tasks/<script>.py`):

| Script | Purpose |
| --- | --- |
| `save_hostnames_to_file.py` | List all robots currently registered with the coordinator and save their hostname/IP to a timestamped CSV. |
| `find_by_hostname.py <hostname>` | Make a single robot identify itself by lighting its top LED red — useful for matching a hostname to a physical robot. |
| `update_swarm.py` | Broadcast an `update_code` command so every Pi pulls the latest platform code and restarts its daemon. |
| `aggregate_logs.py <zip_dir> <out_dir>` | Unzip a session's collected per-robot logs and combine them into one `aggregated.csv`. |
| `plot_trajectories.py <aggregated.csv> <out.png> [hostnames...]` | Plot the reconstructed OptiTrack trajectories of one or more robots from an aggregated CSV. |
| `test_connection.py` | Minimal TCP echo server on port 9000, for manually checking that a Pi is reachable on the network. |
| `test_optitrack.py` | Standalone smoke test that connects to a NatNet server and prints incoming rigid-body timestamps. |

## Utils

### Logging

Every running experiment gets a [`SessionLogger`](swarm_platform/daemon/logger.py) (CSV writer) on its own Pi, created by the daemon when the session starts. Experiment code calls `logger.log(state, command)` each tick; the header is inferred from the combined keys of the first `state`/`command` pair logged, and every row is flushed immediately. Log files live under `logs/<session_id>/<hostname>.csv` on each Pi, managed by [`LogManager`](swarm_platform/daemon/log_manager.py).

Calling `session.collect_logs(output_dir="results")` on the controller streams each robot's log directory back as a zip (in 32KB base64-encoded chunks over the same TCP connection, see [`SwarmDaemon.stream_logs`](swarm_platform/daemon/server.py)) and saves it to `results/<session_id>/<hostname>.zip`. By default the remote copy is then deleted (`delete_remote=True`); call `session.delete_logs()` separately if you want to delete without collecting.

### Post-processing & analysis

Once logs are collected, a few helpers turn the raw per-robot CSVs into something analysable:

- [`swarm_platform/utils/unpack_results.py`](swarm_platform/utils/unpack_results.py) — `unpack_and_aggregate(zip_dir, output_dir)` extracts every `<hostname>.zip` and concatenates the CSVs inside into a single `aggregated.csv` tagged with a `hostname` column (also usable via `tasks/aggregate_logs.py`).
- [`swarm_platform/utils/reconstruct_trajectories.py`](swarm_platform/utils/reconstruct_trajectories.py) — `load_trajectories()`/`plot_trajectories()` reconstruct and plot per-robot OptiTrack paths (`pose.x`/`pose.y`/`pose.z` + orientation + motor columns) from an aggregated CSV (also usable via `tasks/plot_trajectories.py`).
- [`analysis/colour_mean.py`](analysis/colour_mean.py) and [`analysis/colour_spread.py`](analysis/colour_spread.py) — example analysis scripts that compute per-file/per-run mean/std and per-colour statistics over `results/`; adapt these as a starting point for your own project-specific analyses.

## How to cite

A citable release (paper/DOI) for this platform has not been published yet. If you use it in your research in the meantime, please reference the repository directly:

```
Schwarzenbach, L. Thymio Swarm Platform. https://github.com/lmschw/thymio_swarm_platform
```
