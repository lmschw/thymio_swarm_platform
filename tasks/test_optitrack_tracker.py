import time

from swarm_platform.tracking.optitrack_tracker import OptitrackTracker

tracker = OptitrackTracker(
    server_ip="10.0.10.4",
    hostname_map={}
)

tracker.connect()

while True:
    time.sleep(1)