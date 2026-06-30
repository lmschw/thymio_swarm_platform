import json
from dataclasses import asdict, is_dataclass


def encode(msg) -> str:
    if is_dataclass(msg):
        return json.dumps(asdict(msg))
    return json.dumps(msg)


def decode(raw: str):
    return json.loads(raw)