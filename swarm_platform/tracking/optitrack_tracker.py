import asyncio
import threading

import natnet

from .pose import Pose


class OptitrackTracker:

    def __init__(
        self,
        host: str,
        hostname_map: dict[str, str],
    ):
        self.host = host
        self.hostname_map = hostname_map

        self.client = None

        self.robot_ids = {}

        self.latest_poses = {}

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

        definitions = self.client._model_definitions

        names_to_ids = {
            rb.name: rb.id_
            for rb in definitions
            if hasattr(rb, "id_")
        }

        print("Rigid bodies:")
        print(names_to_ids)

        for hostname, rigid_name in self.hostname_map.items():

            if rigid_name not in names_to_ids:
                raise RuntimeError(
                    f"Rigid body '{rigid_name}' "
                    f"for {hostname} not found"
                )

            self.robot_ids[hostname] = (
                names_to_ids[rigid_name]
            )

        print(
            "Robot mapping:",
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

                    self.latest_poses[hostname] = Pose(
                        position=rb.position,
                        orientation=rb.orientation,
                    )


    async def get_pose(
        self,
        hostname: str,
    ):

        return self.latest_poses.get(
            hostname
        )


    async def get_all_poses(self):

        return dict(
            self.latest_poses
        )


    async def stop(self):

        self.running = False