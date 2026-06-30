from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal


@dataclass
class Ping:
    type: Literal["ping"] = "ping"


@dataclass
class Status:
    type: Literal["status"] = "status"


@dataclass
class Stop:
    type: Literal["stop"] = "stop"


@dataclass
class StartExperiment:
    type: Literal["start_experiment"]
    name: str
    config: Optional[Dict[str, Any]] = None