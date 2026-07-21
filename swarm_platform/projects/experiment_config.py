from dataclasses import dataclass

@dataclass
class ExperimentConfig:

    cls: type
    tracking: bool = False