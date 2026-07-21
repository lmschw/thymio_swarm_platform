from dataclasses import dataclass


@dataclass
class Pose:
    position: tuple[float, float, float]
    orientation: tuple[float, float, float, float]