from dataclasses import dataclass


@dataclass(slots=True)
class RobotConfig:

    max_motor: int = 500

    wheel_radius: float = 0.021  # meters

    wheel_distance: float = 0.085  # meters

    sensor_max: int = 4500

    control_frequency: float = 20.0  # Hz