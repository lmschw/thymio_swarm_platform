import yaml
from pathlib import Path


CONFIG_PATH = Path("config.yaml")


def load_config(path: Path = CONFIG_PATH) -> dict:
    if not path.exists():
        return {}

    with open(path, "r") as f:
        return yaml.safe_load(f) or {}