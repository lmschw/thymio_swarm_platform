from dataclasses import dataclass


@dataclass(slots=True)
class RobotCommand:

    left_motor: int = 0

    right_motor: int = 0

    top_led: tuple[int, int, int] = (0, 0, 0)