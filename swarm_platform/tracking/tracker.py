import asyncio
from .pose import Pose


class TrackingClient:

    def __init__(self, hostname):

        self.hostname = hostname

        self.pose = None
        self.poses = {}

        self.running = False


    async def start(self):

        self.running = True

        # Placeholder.
        # Later:
        # connect UDP/WebSocket server

        print(
            "[TRACKING] client started"
        )


    async def stop(self):

        self.running = False


    async def get_pose(self):

        return self.pose


    async def get_all_poses(self):

        return dict(self.poses)