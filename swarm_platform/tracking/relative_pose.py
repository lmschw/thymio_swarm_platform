from dataclasses import dataclass


@dataclass
class RelativePose:
    """Pose of another robot relative to this robot."""

    distance: float
    bearing: float
    orientation_difference: float