from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass
class Pose:
    """A 3D pose (position and orientation) of a tracked object, e.g. a robot.

    Attributes:
        position: The (x, y, z) position.
        orientation: The orientation as a (x, y, z, w) quaternion.
    """

    position: Tuple[float, float, float]
    orientation: Tuple[float, float, float, float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert this pose to a plain dict of JSON-serializable lists.

        Returns:
            A dict with "position" and "orientation" keys, each mapped to a list
            of floats.
        """
        return {
            "position": list(self.position),
            "orientation": list(self.orientation),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Pose":
        """Build a Pose from a dict as produced by `to_dict`.

        Args:
            data: A dict containing "position" and "orientation" sequences.

        Returns:
            The reconstructed Pose instance.
        """
        return cls(
            position=tuple(data["position"]),
            orientation=tuple(data["orientation"]),
        )