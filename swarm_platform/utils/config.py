from dataclasses import dataclass


@dataclass(slots=True)
class RobotConfig:
    """Physical and control parameters for a Thymio robot.

    Attributes:
        max_motor: Maximum motor speed value accepted by the robot.
        wheel_radius: Wheel radius, in meters.
        wheel_distance: Distance between the two wheels, in meters.
        sensor_max: Maximum raw value reported by the proximity/ground sensors.
        control_frequency: Frequency at which the control loop runs, in Hz.
    """

    max_motor: int = 500

    wheel_radius: float = 0.021  # meters

    wheel_distance: float = 0.085  # meters

    sensor_max: int = 4500

    control_frequency: float = 20.0  # Hz