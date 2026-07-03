from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Project:
    name: str
    version: str
    path: Path
    experiments: dict[str, type]