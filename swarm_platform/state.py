from dataclasses import dataclass


@dataclass(slots=True)
class RobotState:

    proximity: list[int]

    ground: list[int]

    accelerometer: list[int]

    buttons: dict[str, bool]

    temperature: int