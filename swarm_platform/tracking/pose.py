from dataclasses import dataclass


@dataclass
class Pose:
    position: tuple[float, float, float]
    orientation: tuple[float, float, float, float]

    def to_dict(self):
        return {
            "position": list(self.position),
            "orientation": list(self.orientation),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            position=tuple(data["position"]),
            orientation=tuple(data["orientation"]),
        )