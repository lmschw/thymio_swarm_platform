import math
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class RelativePose:
    """Pose of another robot relative to this robot."""

    distance: float
    bearing: float
    orientation_difference: float