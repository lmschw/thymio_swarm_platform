from dataclasses import dataclass
from typing import Tuple


@dataclass(slots=True)
class RobotCommand:
    """A single command to be sent to a robot, controlling its motors and top LED.

    Attributes:
        left_motor: Target speed for the left motor.
        right_motor: Target speed for the right motor.
        top_led: RGB color to set the top LED to, as an (r, g, b) tuple.
    """

    left_motor: int = 0

    right_motor: int = 0

    top_led: Tuple[int, int, int] = (0, 0, 0)