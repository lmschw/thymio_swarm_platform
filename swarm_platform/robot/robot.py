import asyncio
import json
import math
import socket
import time
from enum import Enum
from types import TracebackType
from typing import Any, Self

import numpy as np

from ..config import COORDINATOR_IP, COORDINATOR_PORT
from ..protocol.command import RobotCommand
from ..tracking.pose import Pose
from ..tracking.relative_pose import RelativePose
from ..utils.config import RobotConfig
from .camera import Camera
from .connection import ThymioConnection
from .led_ring import LedRing
from .state import RobotState


class _WheelChannelState(Enum):
    NOMINAL = 1,
    HICCUP = 2

class _WheelChannel:
    """
    Time-Delta Scaled H-Bridge Protection Controller.
    Includes Kinematic Tethering, Thermal Bucket Estimation,
    Hiccup Mode, and Zero-Crossing (Plug-Braking) Protection.
    """
    def __init__(self, v_max: float=350.0, a_max: float=400.0, t_stall_max: float=0.4, c_ratio: float=10.0, epsilon: float=5.0) -> None:
        """
        Parameters:
            v_max: float - maximum allowed speed [speed units]
            a_max: float - maximum allowed accelleration [speed units/sec]
            t_stall_max : float - time before thermal damage on short circuit [sec]
            c_ratio : float - thermal dissipation (cooling) ratio as coefficient of t_stall_max
            epsilon: float - tollerance round zero [speed unit]
        """
        # Speed units are actually int but to avoid conversions issues
        # the code use floats everywhere
        self.v_max: float = abs(float(v_max))              # [speed units]
        self.a_max: float = abs(float(a_max))              # [speed units/s] ~> [position/s^2]
        self.t_stall_max: float = abs(float(t_stall_max))  # [s]
        self.c_ratio: float = abs(float(c_ratio))          # Cooling ratio T_cool / T_stall
        self.epsilon: float = abs(float(epsilon))          # Deadband noise floor
        self.y_f_inertia: float = 0.25                     # EMA filter coef on y_m(t)

        # Thermal rates [%/s]
        if self.t_stall_max == 0.0:
            raise ValueError("t_stall_max cannot be zero")

        if self.c_ratio == 0.0:
            raise ValueError("c_ratio cannot be zero")

        self.r_heat: float = 100.0 / self.t_stall_max
        self.r_cool: float = self.r_heat / self.c_ratio

        # State variables
        self.reset()

    def reset(self) -> None:
        self.t_prev: float | None = None
        self.y_f_prev: float | None = None
        self.r_s_prev: float = 0.0
        self.Q: float = 0.0
        self.state: _WheelChannelState = _WheelChannelState.NOMINAL

    def step(self, t, r, y_m) -> tuple[float, float, _WheelChannelState]:
        """
        Executes one tick of the safety layer.

        Parameters:
            t   : float - Current timestamp [s]
            r   : float - Target reference velocity from motion policy
            y_m : float - Raw measured velocity from sensor/firmware

        Returns:
            r_s   : float - Safe reference command to driver
            Q     : float - Current thermal stress level [0-100%]
            state : _WheelChannelState
        """
        # Delta time
        # dt(t) = T(t) - T(t-1)
        if self.t_prev is None:
            dt = 0.1
        else:
            dt = max(t - self.t_prev, 1e-6)

        # Feedback signal filtering
        # y_f(t) = alpha * y_f(t-1) + (1-alpha)*y_m(t)
        if self.y_f_prev is None:
            y_f = y_m
        else:
            y_f = self.y_f_inertia * self.y_f_prev + (1 - self.y_f_inertia) * y_m

        # Dynamic Kinematic Limits
        # E_max = a_max dt
        # DS = .8 E_max
        E_max = self.a_max * dt
        delta_stall = 0.8 * E_max

        # Thermal Estimation
        # stall condition C_s(t) = |y_f(t)| <= eps and |r_s(t-1)| > DS and eps <= 0.5 DS
        #           | R_h  if stalled
        #   dQ(t) = | -R_c if not stalled
        #
        #   Q(t) = clip(Q(t-1) + dQ(t), 0, 100)
        stall_enabled: bool = self.epsilon <= 0.5 * delta_stall  # > 0
        stalled: bool = stall_enabled and (abs(y_f) <= self.epsilon) and (abs(self.r_s_prev) > delta_stall)
        if stalled:
            dQ = self.r_heat * dt
        else:
            dQ = -self.r_cool * dt

        Q = float(np.clip(self.Q + dQ, 0.0, 100.0))

        # State Machine Transition
        # if S(t-1) is NOMINAL and Q(t) >= 100 then S(t) = HICCUP
        # if S(t-1) is HICCUP  and Q(t) <= 0   then S(t) = NOMINAL
        # S(t) = S(t-1) otherwise
        state = self.state
        if self.state == _WheelChannelState.NOMINAL and Q >= 100.0:
            state = _WheelChannelState.HICCUP
        elif self.state == _WheelChannelState.HICCUP and Q <= 0.0:
            state = _WheelChannelState.NOMINAL

        # Acceleration Limiter
        #           | 0           if S(t) is HICCUP
        #  r_a(t) = | clip(r(t), y_f(t)-E_max, y_f(t)+E_max)
        r_a = 0.0 # HICCUP requires to stop
        if state == _WheelChannelState.NOMINAL:
            r_a = float(np.clip(r, y_f - E_max, y_f + E_max))

        # Zero Crossing
        # zero-crossing condition: |y_f(t)|>eps and r_a(t)y_f(t) < 0
        #          | 0         if zero-crossing
        # r_z(t) = | r_a(t)    if not zero-crossing
        zero_cross: bool = (abs(y_f) > self.epsilon) and (r_a * y_f < 0)
        r_z: float = 0.0 if zero_cross else r_a

        # Speed Envelop
        # r_s(t) = clip(r_z(t), -V_max, V_max)
        r_s: float = float(np.clip(r_z, -self.v_max, self.v_max))

        # Memory Update
        self.t_prev = t
        self.y_f_prev = y_f
        self.r_s_prev = r_s
        self.Q = Q
        self.state = state

        return r_s, self.Q, self.state
# _WheelChannel

class MotorProtection:
    """
    Closed-loop motor protection controller for Thymio II wheels.

    Uses a 3-sample median filter on back-EMF speed readings and a
    zero-clamped tracking leash to ensure smooth acceleration, safe
    zero-crossing reversals, and bounded effort when a wheel is stalled.
    """

    def __init__(self, v_max=350.0, a_max=400.0, t_stall_max=0.4, c_ratio=10.0, epsilon=5.0):
        self.left = _WheelChannel(v_max=v_max, a_max=a_max, t_stall_max=t_stall_max, c_ratio=c_ratio, epsilon=epsilon)
        self.right = _WheelChannel(v_max=v_max, a_max=a_max, t_stall_max=t_stall_max, c_ratio=c_ratio, epsilon=epsilon)

    def reset(self):
        self.left.reset()
        self.right.reset()

    def step(self, now, target_speeds, measure_speeds) -> np.ndarray:
        """
        Compute safe target speeds for both wheels.

        Parameters
        ----------
        now: float, current timestamp in seconds
        target_speeds : np.ndarray or list/tuple of length 2
            Desired wheel speeds [left, right].
        measure_speeds : np.ndarray or list/tuple of length 2
            Measured back-EMF wheel speeds [left, right].

        Returns
        -------
        np.ndarray
            Protected integer wheel speed commands [left, right].
        """
        target_arr = np.asarray(target_speeds, dtype=float)
        measure_arr = np.asarray(measure_speeds, dtype=float)

        u_left = self.left.step(now, target_arr[0], measure_arr[0])[0]
        u_right = self.right.step(now, target_arr[1], measure_arr[1])[0]
        return np.array([u_left, u_right], dtype=int)
# MotorProtection

class Robot:

    """
    High-level interface to a single Thymio robot.

    Wraps a :class:`ThymioConnection` to expose motor, LED, sensor and
    proximity-communication operations as simple async methods, and
    tracks the robot's own and swarm-mates' global poses (as reported
    by an external tracking system).
    """

    def __init__(self, config: RobotConfig | None = None,
                 tracker: Any | None = None,
                 protection: MotorProtection|None = None) -> None:
        """
        Initializes the robot with its configuration and optional tracker.

        Args:
            config: The robot's configuration (motor limits, wheel
                geometry, etc.). Defaults to a new ``RobotConfig()``
                with default values if not provided.
            tracker: Optional external tracking client (e.g. an
                OptiTrack client) associated with this robot.
            protection: Optional motor protection implemetation/configuration.
                Overriding the motor protection can destroy the hardware.
        """
        self.config = config or RobotConfig()
        self.connection = ThymioConnection()
        self.camera = Camera()
        self.led_ring = LedRing()
        self.hostname = socket.gethostname()
        self.tracker = tracker
        self.global_poses: dict[str, Pose] = {}
        self.motor_protection = protection if protection is not None else MotorProtection()

    # Context manager
    async def __aenter__(self) -> Self:
        """
        Async context manager entry point; connects to the robot.

        Returns:
            This robot instance, once connected.
        """
        await self.connect()
        return self


    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
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

        Also attempts to start the optional Pi camera and LED ring, if
        attached. Detection of both is best-effort and never raises, so a
        robot missing either (or with a failed one) still connects normally.
        """
        await self.connection.connect()
        await self.camera.start()
        await self.led_ring.start()

    async def disconnect(self) -> None:
        """
        Disconnects from the underlying Thymio node and releases the
        camera and LED ring, if either was started.
        """
        await self.camera.stop()
        await self.led_ring.stop()
        await self.connection.disconnect()

    async def _set_variables(self, var_dict: dict[str, list[int]], timeout: float = 1.0) -> None:
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
        except TimeoutError:
            raise RuntimeError(
                f"Timed out waiting for ack on set_variables({var_dict})"
            )

    # Motors
    async def drive(self, left: int, right: int, now: float|None=None, speeds: list[int]|np.ndarray|None=None) -> None:
        """
        Sets the target speed of the left and right motors
        applying the protection.

        Args:
            left: Target speed for the left motor.
            right: Target speed for the right motor.
            now: Current timestamp, default from time module.
            speeds: Current wheels speeds, default from self.speed()
        """

        if now is None:
            now = time.perf_counter()

        if speeds is None:
            speeds = await self.speed()

        # mandatory to apply the protection before drive
        target = [left, right]
        wheels_vel = self.motor_protection.step(now, target, speeds)

        await self._set_variables({
            "motor.left.target": [int(wheels_vel[0])],
            "motor.right.target": [int(wheels_vel[1])],
        })

    async def stop(self) -> None:
        """
        Stops both motors by setting their target speed to zero.
        ATTENTION: blocking procedure.
        It waits until the robot stops.
        """
        await self.drive(0, 0)
        self.motor_protection.reset()
        """
        """
        start: float = time.perf_counter()
        while time.perf_counter() - start < 5.0:
            wheels_speed = await self.speed()
            await self.drive(0, 0, speeds=wheels_speed)

            y_left = abs(wheels_speed[0])
            y_right = abs(wheels_speed[1])
            if max(y_left, y_right) <= 5:
                break

            await asyncio.sleep(0.05)

        await self.drive(0, 0)
        self.motor_protection.reset()

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
    async def proximity_horizontal(self) -> list[int]:
        """
        Reads the horizontal proximity sensor values.

        Returns:
            The list of horizontal proximity sensor readings.
        """
        await self.connection.process_messages()
        return list(self.connection.node.var.get("prox.horizontal"))

    async def proximity_ground_delta(self) -> list[int]:
        """
        Reads the ground proximity sensor delta values.

        Returns:
            The list of ground proximity delta readings.
        """
        await self.connection.process_messages()
        return list(self.connection.node.var.get("prox.ground.delta"))

    async def proximity_ground_reflected(self) -> list[int]:
        """
        Reads the ground proximity sensor reflected light values.

        Returns:
            The list of ground proximity reflected-light readings.
        """
        await self.connection.process_messages()
        return list(self.connection.node.var.get("prox.ground.reflected"))

    async def proximity_ground_ambiant(self) -> list[int]:
        """
        Reads the ground proximity sensor ambient light values.

        Returns:
            The list of ground proximity ambient-light readings.
        """
        await self.connection.process_messages()
        return list(self.connection.node.var.get("prox.ground.ambiant"))

    async def buttons(self) -> dict[str, bool]:
        """
        Reads the state of the robot's buttons.

        Returns:
            A dictionary mapping each button name ("forward",
            "backward", "left", "right", "center") to its pressed state.
        """
        await self.connection.process_messages()
        return {
            "forward": bool(self.connection.node.var.get("button.forward")[0]),
            "backward": bool(self.connection.node.var.get("button.backward")[0]),
            "left": bool(self.connection.node.var.get("button.left")[0]),
            "right": bool(self.connection.node.var.get("button.right")[0]),
            "center": bool(self.connection.node.var.get("button.center")[0]),
        }

    async def accelerometer(self) -> list[int]:
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

    async def camera_capture(self, path: str | None = None) -> bytes:
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

    # LED ring
    @property
    def has_led_ring(self) -> bool:
        """
        Whether this robot has a working RGB LED ring attached.

        Returns:
            True if a ring was detected and started successfully.
        """
        return self.led_ring.available

    async def led_ring_fill(self, r: int, g: int, b: int) -> None:
        """
        Sets every pixel on the LED ring to the same color.

        Args:
            r: Red channel value (0-255).
            g: Green channel value (0-255).
            b: Blue channel value (0-255).

        Raises:
            LedRingError: If this robot has no LED ring available.
        """
        await self.led_ring.fill(r, g, b)

    async def led_ring_set_pixel(self, index: int, r: int, g: int, b: int) -> None:
        """
        Sets a single LED ring pixel's color.

        Args:
            index: Index of the pixel to set (0-based).
            r: Red channel value (0-255).
            g: Green channel value (0-255).
            b: Blue channel value (0-255).

        Raises:
            LedRingError: If this robot has no LED ring available.
        """
        await self.led_ring.set_pixel(index, r, g, b)

    async def led_ring_set_pixels(self, colors: list[tuple[int, int, int]]) -> None:
        """
        Sets all LED ring pixel colors at once.

        Args:
            colors: A list of (r, g, b) tuples, one per pixel, in order.

        Raises:
            LedRingError: If this robot has no LED ring available.
        """
        await self.led_ring.set_pixels(colors)

    async def led_ring_off(self) -> None:
        """Turns off every pixel on the LED ring. A no-op if no ring is available."""
        await self.led_ring.off()

    async def speed(self) -> list[int]:
        """
        Read the current wheels speed from back-EMF sensors

        Return:
            [left, right] as estimated wheels speeds.
        """
        await self.connection.process_messages()
        left = self.connection.node.var.get("motor.left.speed")[0]
        right = self.connection.node.var.get("motor.right.speed")[0]
        return [left, right]

    async def state(self) -> RobotState:
        """
        Reads the robot's full sensor/actuator state.

        Returns:
            A ``RobotState`` snapshot containing the proximity, ground,
            accelerometer, button and temperature readings.
        """
        return RobotState(
            proximity=await self.proximity_horizontal(),
            ground=await self.proximity_ground_reflected(),
            accelerometer=await self.accelerometer(),
            buttons=await self.buttons(),
            temperature=await self.temperature(),
            speed=await self.speed()
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

    async def receive(self) -> tuple[int, list[int], int, int]:
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

    async def exchange_swarm_info(
        self,
        my_id: str,
        data: dict[str, Any],
        timeout: float = 0.5,
    ) -> dict[str, dict[str, Any]]:
        """
        Optional, opt-in swarm-wide info exchange via the coordinator.

        Pushes ``data`` for this robot (keyed by ``my_id``) up to the
        coordinator and returns its current merged ``{id: data}`` dict
        for the whole swarm, in the same round trip. Unlike
        ``send``/``receive`` (the Thymio's bandwidth-limited prox.comm
        link - one small message per tick, no sender id, only reaches
        whoever's currently in IR range), this goes over the existing
        coordinator TCP connection already used for
        registration/heartbeats, so it carries arbitrary-size/precision
        JSON and reaches every robot in the swarm. Decision-making code
        that still wants a locality restriction (only consult *nearby*
        robots' info) should combine this with its own proximity signal
        - e.g. a lightweight id-only prox.comm broadcast - and filter
        the returned dict down to ids it has recently seen that way.

        This is entirely opt-in: nothing calls it unless an experiment
        does, so robots/experiments that never call it are unaffected.

        Args:
            my_id: Key this robot's data is stored under (e.g. a short
                per-robot id).
            data: JSON-serializable payload to publish for this robot.
            timeout: Seconds to wait for the coordinator before giving up.

        Returns:
            The coordinator's current ``{id: data}`` dict, including
            this robot's own just-pushed entry. Returns ``{}`` if the
            coordinator is unreachable or times out, rather than
            raising - a transient coordinator hiccup should never stall
            a control loop tick.
        """
        msg = {"type": "info_update", "id": str(my_id), "data": data}

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(COORDINATOR_IP, COORDINATOR_PORT),
                timeout=timeout,
            )
            try:
                writer.write((json.dumps(msg) + "\n").encode())
                await writer.drain()
                raw = await asyncio.wait_for(reader.readline(), timeout=timeout)
            finally:
                writer.close()
                await writer.wait_closed()
        except Exception: # noqa: BLE001
            return {}

        if not raw:
            return {}

        try:
            reply = json.loads(raw.decode())
        except Exception: # noqa: BLE001
            return {}

        return reply.get("data", {})

    async def get_global_pose(self) -> Pose | None:
        """
        Retrieves this robot's own global pose from the tracked poses.

        Returns:
            This robot's ``Pose`` (looked up by its hostname), or
            ``None`` if it is not present in ``global_poses``.
        """
        poses = self.global_poses
        return poses.get(self.hostname)

    async def get_all_global_poses(self) -> dict[str, Pose]:
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
            2.0 * (w * y + z * x),
            1.0 - 2.0 * (x * x + y * y),
        )


    def normalize_angle(self, angle: float) -> float:
        """Normalize an angle to [-pi, pi]."""
        return (angle + math.pi) % (2.0 * math.pi) - math.pi


    async def get_relative_poses(
        self,
        hostnames: list[str] | None = None,
    ) -> dict[str, RelativePose]:

        poses = await self.get_all_global_poses()
        own_pose = poses.get(self.hostname)
        if own_pose is None:
            return {}
        ox, _, oz = own_pose.position

        own_yaw = self.quaternion_to_yaw(own_pose.orientation)

        relative_poses = {}

        # Use a set for efficient membership checks.
        hostname_filter = set(hostnames) if hostnames is not None else None

        relative_poses: dict[str, RelativePose] = {}

        for hostname, pose in poses.items():
            # Never include ourselves.
            if hostname == self.hostname:
                continue

            # If a filter was provided, only include requested robots.
            if hostname_filter is not None and hostname not in hostname_filter:
                continue

            x, _, z = pose.position

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
    ) -> list[str]:
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

        sin_yaw = 2.0 * (w * y + z * x)
        cos_yaw = 1.0 - 2.0 * (x * x + y * y)

        return math.atan2(sin_yaw, cos_yaw)


    @staticmethod
    def _normalize_angle(angle: float) -> float:
        """
        Normalize an angle to [-pi, pi].
        """
        return (angle + math.pi) % (2.0 * math.pi) - math.pi

