import threading
import natnet
import asyncio

from typing import Any, Dict, List

from swarm_platform.tracking.pose import Pose


class _QuietNatNetLogger(natnet.Logger):
    """Suppresses the NatNet SDK's per-frame debug/info chatter (clock sync, etc.)."""

    def debug(self, msg: str, *args: Any) -> None:
        """Discard a debug-level log message from the NatNet SDK.

        Args:
            msg: The debug message (ignored).
            *args: Additional positional arguments accompanying the message
                (ignored).
        """
        pass

    def info(self, msg: str, *args: Any) -> None:
        """Discard an info-level log message from the NatNet SDK.

        Args:
            msg: The info message (ignored).
            *args: Additional positional arguments accompanying the message
                (ignored).
        """
        pass


class OptitrackClient:
    """Client for the OptiTrack motion-capture system via the NatNet SDK.

    Connects to a NatNet server, maps rigid bodies to robot hostnames, and
    continuously receives pose updates on a background thread.
    """

    def __init__(
        self,
        host: str,
        hostname_map: dict[str, str],
        verbose: bool = False,
    ) -> None:
        """Initialize the client configuration without connecting.

        Args:
            host: Address of the NatNet server to connect to.
            hostname_map: Mapping from robot hostname to the rigid body
                name configured in Motive.
            verbose: If True, enable verbose NatNet SDK logging and status
                print statements.
        """
        self.host = host
        self.hostname_map = hostname_map
        self.verbose = verbose

        self.client = None

        self.robot_ids = {}
        self.poses = {}

        self.running = False
        self.thread = None


    async def start(self) -> None:
        """Connect to the NatNet server and start receiving poses.

        Connects the NatNet client, builds the rigid-body-to-hostname
        mapping, registers the frame callback, and starts a background
        thread that spins the client. Waits (asynchronously) until at
        least one pose has been received or a timeout elapses.

        Raises:
            RuntimeError: If no OptiTrack poses are received within the
                startup timeout.
        """

        self.client = natnet.Client.connect(
            self.host,
            timeout=10,
            logger=natnet.Logger() if self.verbose else _QuietNatNetLogger(),
        )

        if self.verbose:
            print("OptiTrack connected")

        self._build_mapping()

        self.client.set_callback(
            self._callback
        )

        self.running = True

        self.thread = threading.Thread(
            target=self._spin,
            daemon=True,
        )

        self.thread.start()

        # Wait for first frame
        timeout = 5
        start = asyncio.get_event_loop().time()

        while not self.poses:

            if asyncio.get_event_loop().time() - start > timeout:
                raise RuntimeError(
                    "No OptiTrack poses received"
                )

            await asyncio.sleep(0.05)

        if self.verbose:
            print(
                "Initial poses received:",
                self.poses,
            )

    def _build_mapping(self) -> None:
        """Build the mapping from robot hostname to NatNet rigid body id.

        Reads the rigid body definitions from the connected NatNet client
        and resolves each configured hostname's rigid body name to its
        NatNet id, populating ``self.robot_ids``.

        Raises:
            RuntimeError: If a configured rigid body name is not present
                in the NatNet model definitions.
        """
        names = {
            rb.name: rb.id_
            for rb in self.client._model_definitions
            if hasattr(rb, "id_")
        }
        print(names)
        for hostname, rigid_name in self.hostname_map.items():
            if rigid_name not in names:
                raise RuntimeError(
                    f"Rigid body {rigid_name} missing"
                )
            self.robot_ids[hostname] = names[rigid_name]

        if self.verbose:
            print(
                "Tracking map:",
                self.robot_ids
            )

    def _spin(self) -> None:
        """Run the NatNet client's blocking spin loop until stopped.

        Intended to run on a background thread. Repeatedly calls
        ``self.client.spin()`` until ``self.running`` becomes False; if
        the call raises, the error is printed and the loop stops.
        """

        while self.running:
            try:
                self.client.spin()
            except Exception as e:
                print(
                    f"[NATNET ERROR] {e}",
                    flush=True,
                )
                break

    def _callback(
        self,
        rigid_bodies: List[Any],
        markers: Any,
        timing: Any,
    ) -> None:
        """Handle a NatNet frame update by recording tracked robot poses.

        Registered with the NatNet client as its per-frame callback. For
        each rigid body in the frame, updates the pose of any hostname
        whose mapped rigid body id matches that rigid body's id.

        Args:
            rigid_bodies: Rigid bodies reported in this frame, each
                exposing ``id_``, ``position`` and ``orientation``.
            markers: Unlabeled marker data reported in this frame
                (unused).
            timing: Timing information for this frame (unused).
        """
        for rb in rigid_bodies:
            for hostname, rb_id in self.robot_ids.items():
                if rb.id_ == rb_id:
                    self.poses[hostname] = Pose(
                        position=rb.position,
                        orientation=rb.orientation,
                    )

    async def get_all_poses(self) -> Dict[str, Pose]:
        """Get a snapshot of the most recently received robot poses.

        Returns:
            A copy of the hostname-to-pose mapping.
        """
        return dict(
            self.poses
        )

    def stop(self) -> None:
        """Signal the background spin thread to stop."""
        self.running = False