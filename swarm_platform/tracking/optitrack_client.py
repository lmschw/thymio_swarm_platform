import threading
import natnet

from swarm_platform.tracking.pose import Pose

class OptitrackClient:
    def __init__(
        self,
        host: str,
        hostname_map: dict[str, str],
    ):
        self.host = host
        self.hostname_map = hostname_map

        self.client = None

        self.robot_ids = {}
        self.poses = {}

        self.running = False
        self.thread = None


    async def start(self):
        self.client = natnet.Client.connect(
            self.host,
            timeout=10,
        )
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

    def _build_mapping(self):
        names = {
            rb.name: rb.id_
            for rb in self.client._model_definitions
            if hasattr(rb, "id_")
        }
        for hostname, rigid_name in self.hostname_map.items():
            if rigid_name not in names:
                raise RuntimeError(
                    f"Rigid body {rigid_name} missing"
                )
            self.robot_ids[hostname] = names[rigid_name]

        print(
            "Tracking map:",
            self.robot_ids
        )

    def _spin(self):
        while self.running:
            self.client.spin()

    def _callback(
        self,
        rigid_bodies,
        markers,
        timing,
    ):
        for rb in rigid_bodies:
            for hostname, rb_id in self.robot_ids.items():
                if rb.id_ == rb_id:
                    self.poses[hostname] = Pose(
                        position=rb.position,
                        orientation=rb.orientation,
                    )

    async def get_all_poses(self):
        return dict(
            self.poses
        )

    def stop(self):
        self.running = False