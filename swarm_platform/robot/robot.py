import asyncio
import socket
from typing import Any, Dict, List, Optional, Tuple
import math

from .camera import Camera
from .connection import ThymioConnection
from .state import RobotState
from ..protocol.command import RobotCommand
from ..utils.config import RobotConfig
from ..tracking.pose import Pose
from ..tracking.relative_pose import RelativePose

class Robot:

    """
    High-level interface to a single Thymio robot.

    Wraps a :class:`ThymioConnection` to expose motor, LED, sensor and
    proximity-communication operations as simple async methods, and
    tracks the robot's own and swarm-mates' global poses (as reported
    by an external tracking system).
    """

    def __init__(self, config: Optional[RobotConfig] = None, tracker: Optional[Any] = None) -> None:
        """
        Initializes the robot with its configuration and optional tracker.

        Args:
            config: The robot's configuration (motor limits, wheel
                geometry, etc.). Defaults to a new ``RobotConfig()``
                with default values if not provided.
            tracker: Optional external tracking client (e.g. an
                OptiTrack client) associated with this robot.
        """
        self.config = config or RobotConfig()
        self.connection = ThymioConnection()
        self.camera = Camera()
        self.hostname = socket.gethostname()
        self.tracker = tracker
        self.global_poses: Dict[str, Pose] = {}

    # Context manager
    async def __aenter__(self) -> "Robot":
        """
        Async context manager entry point; connects to the robot.

        Returns:
            This robot instance, once connected.
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """
        Async context manager exit point; stops the motors and disconnects.

        Args:
            exc_type: The exception type raised in the ``with`` block, if any.
            exc: The exception instance raised in the ``with`` block, if any.
            tb: The traceback of the exception raised in the ``with`` block, if any.
        """
        try:
            await self.stop()
        finally:
            await self.disconnect()


    # Connection
    async def connect(self) -> None:
        """
        Connects to the underlying Thymio node.

        Also attempts to start the optional Pi camera, if one is
        attached. Camera detection is best-effort and never raises, so a
        robot with no camera (or a failed camera) still connects normally.
        """
        await self.connection.connect()
        await self.camera.start()

    async def disconnect(self) -> None:
        """
        Disconnects from the underlying Thymio node and releases the
        camera, if one was started.
        """
        await self.camera.stop()
        await self.connection.disconnect()

    async def _set_variables(self, var_dict: Dict[str, List[int]], timeout: float = 1.0) -> None:
        """
        Sets Thymio VM variables and waits for the acknowledgment.

        Args:
            var_dict: Mapping of Thymio variable names to the values to
                assign to them.
            timeout: Maximum number of seconds to wait for the ack.

        Raises:
            RuntimeError: If no acknowledgment is received before the
                timeout elapses.
        """
        try:
            await asyncio.wait_for(
                self.connection.node.set_variables(var_dict),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Timed out waiting for ack on set_variables({var_dict})"
            )

    # Motors
    async def drive(self, left: int, right: int) -> None:
        """
        Sets the target speed of the left and right motors.

        Args:
            left: Target speed for the left motor.
            right: Target speed for the right motor.
        """

        await self._set_variables({
            "motor.left.target": [int(left)],
            "motor.right.target": [int(right)],
        })

    async def stop(self) -> None:
        """
        Stops both motors by setting their target speed to zero.
        """
        await self.drive(0, 0)

    # LEDs
    async def top_led(self, r: int, g: int, b: int) -> None:
        """
        Sets the color of the robot's top LED.

        Args:
            r: Red channel value.
            g: Green channel value.
            b: Blue channel value.
        """
        await self._set_variables({
            "leds.top": [int(r), int(g), int(b)]
        })

    # Sensors
    async def proximity_horizontal(self) -> List[int]:
        """
        Reads the horizontal proximity sensor values.

        Returns:
            The list of horizontal proximity sensor readings.
        """
        await self.connection.process_messages()
        return list(self.connection.node.var.get("prox.horizontal"))

    async def proximity_ground_delta(self) -> List[int]:
        """
        Reads the ground proximity sensor delta values.

        Returns:
            The list of ground proximity delta readings.
        """
        await self.connection.process_messages()
        return list(self.connection.node.var.get("prox.ground.delta"))

    async def proximity_ground_reflected(self) -> List[int]:
        """
        Reads the ground proximity sensor reflected light values.

        Returns:
            The list of ground proximity reflected-light readings.
        """
        await self.connection.process_messages()
        return list(self.connection.node.var.get("prox.ground.reflected"))

    async def proximity_ground_ambiant(self) -> List[int]:
        """
        Reads the ground proximity sensor ambient light values.

        Returns:
            The list of ground proximity ambient-light readings.
        """
        await self.connection.process_messages()
        return list(self.connection.node.var.get("prox.ground.ambiant"))

    async def buttons(self) -> Dict[str, bool]:
        """
        Reads the state of the robot's buttons.

        Returns:
            A dictionary mapping each button name ("forward",
            "backward", "left", "right", "center") to its pressed state.
        """
        await self.connection.process_messages()
        return {
            "forward": self.connection.node.var.get("button.forward"),
            "backward": self.connection.node.var.get("button.backward"),
            "left": self.connection.node.var.get("button.left"),
            "right": self.connection.node.var.get("button.right"),
            "center": self.connection.node.var.get("button.center"),
        }

    async def accelerometer(self) -> List[int]:
        """
        Reads the accelerometer values.

        Returns:
            The list of accelerometer readings.
        """
        await self.connection.process_messages()
        return list(self.connection.node.var.get("acc"))

    async def temperature(self) -> int:
        """
        Reads the robot's temperature sensor value.

        Returns:
            The temperature reading.
        """
        await self.connection.process_messages()
        return self.connection.node["temperature"]

    # Camera
    @property
    def has_camera(self) -> bool:
        """
        Whether this robot has a working Pi camera attached.

        Returns:
            True if a camera was detected and started successfully.
        """
        return self.camera.available

    async def camera_capture(self, path: Optional[str] = None) -> bytes:
        """
        Captures a still image from the robot's Pi camera.

        Args:
            path: If given, the captured JPEG bytes are also written to
                this filesystem path.

        Returns:
            The captured frame, JPEG-encoded.

        Raises:
            CameraError: If this robot has no camera available.
        """
        return await self.camera.capture(path)

    async def state(self) -> RobotState:
        """
        Reads the robot's full sensor/actuator state.

        Returns:
            A ``RobotState`` snapshot containing the proximity, ground,
            accelerometer, button and temperature readings.
        """
        return RobotState(
            proximity=await self.proximity_horizontal(),
            ground=await self.proximity_ground_delta(),
            accelerometer=await self.accelerometer(),
            buttons=await self.buttons(),
            temperature=await self.temperature(),
        )
    
    async def apply(self, command: RobotCommand) -> None:
        """
        Applies a robot command by driving the motors and setting the top LED.

        Args:
            command: The command containing the target motor speeds and
                top LED color to apply.
        """
        await self.drive(
            command.left_motor,
            command.right_motor,
        )

        await self.top_led(*command.top_led)

    async def send(self, value: int) -> None:
        """
        Sends a value over proximity communication (prox.comm.tx).

        Args:
            value: The value to broadcast to nearby robots.
        """
        value = int(value)

        await self._set_variables({
            "prox.comm.tx": [value],
        })

        self.connection.client.process_waiting_messages()

    async def receive(self) -> Tuple[int, List[int], int, int]:
        """
        Reads the last received proximity communication value and intensities.

        Splits the per-sensor intensities into a front sum (sensors 0-4)
        and a rear sum (sensors 5-6).

        Returns:
            A tuple of ``(rx, intensities, front_intensity,
            rear_intensity)`` where ``rx`` is the last received value,
            ``intensities`` is the list of per-sensor intensities,
            ``front_intensity`` is the sum of the front sensor
            intensities, and ``rear_intensity`` is the sum of the rear
            sensor intensities.
        """
        await self.connection.process_messages()
        rx = self.connection.node.var.get("prox.comm.rx")
        intensities = self.connection.node.var.get("prox.comm.rx._intensities")
        front_intensity = intensities[0] + intensities[1] + intensities[2] + intensities[3] + intensities[4]
        rear_intensity = intensities[5] + intensities[6]
        return rx[0], intensities, front_intensity, rear_intensity

    async def get_global_pose(self) -> Optional[Pose]:
        """
        Retrieves this robot's own global pose from the tracked poses.

        Returns:
            This robot's ``Pose`` (looked up by its hostname), or
            ``None`` if it is not present in ``global_poses``.
        """
        poses = self.global_poses
        return poses.get(self.hostname)

    async def get_all_global_poses(self) -> Dict[str, Pose]:
        """
        Retrieves the global poses of all tracked robots.

        Returns:
            A shallow copy of the ``hostname -> Pose`` mapping of all
            currently tracked robots.
        """
        return dict(
            self.global_poses
        )

    def quaternion_to_yaw(
        self,
        quaternion: tuple[float, float, float, float]
    ) -> float:
        """Convert an (x, y, z, w) quaternion to yaw in radians."""
        x, y, z, w = quaternion

        return math.atan2(
            2.0 * (w * z + x * y),
            1.0 - 2.0 * (y * y + z * z),
        )


    def normalize_angle(self, angle: float) -> float:
        """Normalize an angle to [-pi, pi]."""
        return (angle + math.pi) % (2.0 * math.pi) - math.pi


    async def get_relative_poses(
        self,
    ) -> Dict[str, RelativePose]:

        poses = await self.get_all_global_poses()
        own_pose = await self.get_global_pose()
        ox, _, oz = own_pose.position

        own_yaw = self.quaternion_to_yaw(own_pose.orientation)

        relative_poses = {}

        for hostname, pose in poses.items():
            x, y, z = pose.position

            # Position difference
            dx = x - ox
            dz = z - oz

            # Distance
            distance = math.sqrt(
                dx**2 + dz**2
            )

            # Bearing in world frame
            bearing = self.normalize_angle(
                math.atan2(dz, dx) - own_yaw
            )

            # Other robot's yaw
            other_yaw = self.quaternion_to_yaw(pose.orientation)

            # Orientation difference
            orientation_difference = self.normalize_angle(
                other_yaw - own_yaw
            )

            relative_poses[hostname] = RelativePose(
                distance=distance,
                bearing=bearing,
                orientation_difference=orientation_difference,
            )

        return relative_poses

    async def get_neighbours(
        self,
        perception_range: float,
    ) -> List[str]:
        """
        Returns all robots within perception range.

        Args:
            perception_range:
                Maximum distance at which another robot is considered
                a neighbour.

        Returns:
            A list of hostnames of neighbouring robots.
        """
        relative_poses = await self.get_relative_poses()

        return [
            hostname
            for hostname, relative_pose in relative_poses.items()
            if relative_pose.distance <= perception_range
        ]


    @staticmethod
    def _quaternion_to_yaw(
        quaternion: tuple[float, float, float, float],
    ) -> float:
        """
        Convert an (x, y, z, w) quaternion to yaw.

        Returns:
            Yaw angle in radians.
        """
        x, y, z, w = quaternion

        sin_yaw = 2.0 * (w * z + x * y)
        cos_yaw = 1.0 - 2.0 * (y * y + z * z)

        return math.atan2(sin_yaw, cos_yaw)


    @staticmethod
    def _normalize_angle(angle: float) -> float:
        """
        Normalize an angle to [-pi, pi].
        """
        return (angle + math.pi) % (2.0 * math.pi) - math.pi