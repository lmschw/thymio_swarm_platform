"""Central place for the coordinator's network address.

Every controller-side script and the daemon import ``COORDINATOR_IP``/
``COORDINATOR_PORT`` from here instead of hardcoding them, so the address
only needs to change in one place. Both can still be overridden per-machine
without touching code via the ``SWARM_COORDINATOR``/``SWARM_COORDINATOR_PORT``
environment variables (the same ones used in ``/etc/swarm-platform.conf`` on
the Pis).
"""

import os

COORDINATOR_IP = os.getenv("SWARM_COORDINATOR", "10.15.2.63")
COORDINATOR_PORT = int(os.getenv("SWARM_COORDINATOR_PORT", "9100"))
