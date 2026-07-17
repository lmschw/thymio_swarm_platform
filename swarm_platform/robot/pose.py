from dataclasses import dataclass


@dataclass(slots=True)
class Pose:
    x: float
    y: float
    z: float

    qw: float
    qx: float
    qy: float
    qz: float