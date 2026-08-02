from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal


@dataclass
class Ping:
    """A liveness-check message sent to confirm a robot/daemon is responsive.

    Attributes:
        type: Discriminator identifying this message as a ping.
    """

    type: Literal["ping"] = "ping"


@dataclass
class Status:
    """A request for the current status of a robot/daemon.

    Attributes:
        type: Discriminator identifying this message as a status request.
    """

    type: Literal["status"] = "status"


@dataclass
class Stop:
    """A message instructing the recipient to stop the current activity.

    Attributes:
        type: Discriminator identifying this message as a stop command.
    """

    type: Literal["stop"] = "stop"


@dataclass
class StartExperiment:
    """A message instructing a robot/daemon to start running an experiment.

    Attributes:
        type: Discriminator identifying this message as a start-experiment command.
        name: The name of the experiment to start.
        config: Optional experiment-specific configuration values.
    """

    type: Literal["start_experiment"]
    name: str
    config: Optional[Dict[str, Any]] = None