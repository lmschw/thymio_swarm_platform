from dataclasses import dataclass
from typing import Dict, List


@dataclass(slots=True)
class RobotState:
    """A snapshot of a Thymio robot's sensor readings at a point in time.

    Attributes:
        proximity: Readings from the horizontal proximity sensors.
        ground: Readings from the ground sensors.
        accelerometer: Readings from the 3-axis accelerometer.
        buttons: Mapping of button name to whether it is currently pressed.
        temperature: Current temperature reading.
    """

    proximity: List[int]

    ground: List[int]

    accelerometer: List[int]

    buttons: Dict[str, bool]

    temperature: int