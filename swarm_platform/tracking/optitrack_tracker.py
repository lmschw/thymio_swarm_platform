from __future__ import annotations

import asyncio

import natnet
from natnet.comms import TimestampAndLatency
from natnet.protocol.MocapFrameMessage import (
    LabelledMarker,
    RigidBody,
)

from ..robot.pose import Pose


class OptitrackTracker():

    def __init__(
        self,
        server: str,
        hostname_to_rigid_body: dict[str, int],
    ):
        self.server = server
        self.hostname_to_rigid_body = hostname_to_rigid_body

        self.client = None
        self.task = None

        self._poses: dict[str, Pose] = {}
        self.timestamp = None

    async def start(self):

        if self.client is not None:
            return

        self.client = natnet.Client.connect(
            self.server,
            timeout=10,
        )

        self.client.set_callback(self._callback)

        self.task = asyncio.create_task(
            asyncio.to_thread(self.client.spin)
        )

    async def stop(self):

        if self.client is None:
            return

        self.client.stop()

        if self.task is not None:
            await self.task
            self.task = None

        self.client = None

    async def pose(self, hostname: str) -> Pose | None:
        return self._poses.get(hostname)

    async def poses(self) -> dict[str, Pose]:
        return dict(self._poses)

    def _callback(
        self,
        rigid_bodies: list[RigidBody],
        markers: list[LabelledMarker],
        timing: TimestampAndLatency,
    ):

        self.timestamp = timing.timestamp

        lookup = {
            rb.id_: rb
            for rb in rigid_bodies
        }

        for hostname, rigid_body_id in self.hostname_to_rigid_body.items():

            rb = lookup.get(rigid_body_id)

            if rb is None:
                continue

            self._poses[hostname] = Pose(
                x=rb.position.x,
                y=rb.position.y,
                z=rb.position.z,
                qx=rb.orientation.x,
                qy=rb.orientation.y,
                qz=rb.orientation.z,
                qw=rb.orientation.w,
            )