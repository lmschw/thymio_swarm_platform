from dataclasses import dataclass


@dataclass
class ExperimentConfig:
    """Configuration describing how a single experiment should be run.

    Attributes:
        cls: The experiment class to instantiate and run.
        tracking: Whether external position tracking should be enabled for this experiment.
    """

    cls: type
    tracking: bool = False